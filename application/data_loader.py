"""Application bootstrap use case for loading the active user's data.

Performance notes
-----------------
This module sits on the hot path of EVERY Streamlit re-render (see the
top-level ``load_persistent_data()`` call in ``app.py``) so it pays for
itself to cache the two expensive operations here:

* The exercise catalog is immutable at runtime — cached indefinitely via
  ``_load_exercise_catalog`` (streamlit ``@st.cache_resource``).
* The per-user Supabase data (profile / plan / history) is cached with a
  short TTL so saves become visible quickly but widget interactions that
  do not mutate storage hit the in-memory cache.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from config.settings import DATA_DIR
from infrastructure import storage
from domain.warmup_cooldown import attach_to_weekly_plan

try:
    import streamlit as st
except ImportError:  # Module still importable outside Streamlit.
    st = None


# ==========================================================================
# CACHE BUST — exported FIRST so it is always importable even if the
# Streamlit decorator factory setup below has issues during boot.
# ==========================================================================

def bust_user_cache() -> None:
    """Invalidate the short-lived user-data cache after a write operation.

    Presentation/save code paths should call this immediately after a
    successful profile save, workout-plan save, or history-log save so the
    next render reflects the freshly persisted values.
    """
    if st is None:
        return
    try:
        st.cache_data.clear()
    except Exception:
        pass


# ==========================================================================
# DECORATOR FACTORIES — wrap cache_* calls in try/except so a Streamlit
# runtime-not-initialized window does not abort the whole module import.
# ==========================================================================

def _cache_resource_if_streamlit(func):
    """Apply ``st.cache_resource`` only when Streamlit is importable."""
    if st is None:
        return func
    try:
        return st.cache_resource(show_spinner=False)(func)
    except Exception:
        # Runtime may not be initialized yet on the very first import.
        # Fall back to a trivial pass-through; decorator will be re-tried
        # on the next render cycle when cache_resource is ready.
        return func


def _cache_data_if_streamlit(ttl: int = 10):
    """Apply ``st.cache_data`` with a short TTL when Streamlit is available."""
    def _decorator(func):
        if st is None:
            return func
        try:
            return st.cache_data(ttl=ttl, show_spinner=False)(func)
        except Exception:
            return func
    return _decorator


@_cache_resource_if_streamlit
def _load_exercise_catalog(
    exercises_file: str | Path,
    _warning_callback: Callable[[str], Any] | None,
) -> list[Any]:
    """Load the exercise catalog once per process lifetime.

    First we attempt the Supabase copy, then fall back to the JSON seed on
    disk.  Either way the result is cached as a Streamlit resource so
    subsequent renders reuse the same list without re-querying the network
    or filesystem.

    Note: ``_warning_callback`` is prefixed with an underscore to skip
    Streamlit's hashing step (callbacks are bound methods that cannot
    be hashed).  The catalog's cached result is independent of which
    warning callback is used so this is safe.
    """
    catalog: list[Any] = []
    if storage.is_supabase_available():
        try:
            client = storage._get_supabase_client()
            if client is not None:
                response = client.table("exercises").select("*").execute()
                if response.data:
                    catalog = list(response.data)
        except Exception as error:
            if _warning_callback is not None:
                _warning_callback(
                    "The Supabase exercise catalog could not be loaded. "
                    f"Details: {error}"
                )
    if not catalog:
        catalog = list(storage.load_json(exercises_file, []))
    return catalog


@_cache_data_if_streamlit(ttl=10)
def _load_user_data(
    user_id: str,
    _profile_file: str | Path,
    _workout_plan_file: str | Path,
    _workout_history_file: str | Path,
) -> tuple[Any, Any, Any, str | None, str]:
    """Fetch a user's profile/plan/history from Supabase, cached for 10 s.

    The 10 second TTL keeps the UI snappy for read-heavy interactions
    (tabbing between Dashboard/Profile/Workout) while still picking up
    freshly-saved data within a single digit number of seconds after a
    write.  Callers call :func:`bust_user_cache` right after persisting.

    File path params are underscore-prefixed because they are unused inside
    this routine (we always go to Supabase) but kept on the signature
    for call-site symmetry with ``load_persistent_data`` and to avoid
    Streamlit trying to hash ``pathlib.Path`` objects unnecessarily.
    """
    if not (storage.is_supabase_available() and storage.supabase_schema_ready()):
        return {}, [], [], None, "unavailable"
    try:
        # ---- Credit #4 batched RPC path: 1 HTTP call replaces 3 SELECTs ----
        snapshot = storage.load_all_user_data_for(user_id)
        if snapshot is None:
            return {}, [], [], None, "unavailable"
        profile = snapshot.get("profile") or {}
        profile_id = snapshot.get("profile_id")
        workout_plan = snapshot.get("workout_plan")
        workout_history = snapshot.get("workout_history") or []
        # ---- Credit #4 plan coercion fix -------------------------------
        # The previous coercer ran ``list(workout_plan)`` when plan was a
        # dict (e.g. ``{name, days:[...]}``) which returned a LIST OF THE
        # DICT'S KEY-STRINGS instead of the days list.  We now:
        #   * pass list through unchanged
        #   * unwrap dict plan.payloads (days / schedule / exercises /
        #     weekly_plan / plan) into their list payload OR pass the
        #     whole dict as a single-item list of wrapped dicts so
        #     downstream "for day in plan: draw expander" code sees the
        #     plan content without UI breakage.
        if isinstance(workout_plan, list):
            pass  # already what callers want
        elif isinstance(workout_plan, dict):
            plan = workout_plan
            found: list | None = None
            for key in ("days", "schedule", "weekly_plan", "workouts",
                        "exercises", "plan"):
                candidate = plan.get(key)
                if isinstance(candidate, list) and candidate:
                    found = candidate
                    break
            if found is not None:
                workout_plan = found
            else:
                # Dict plan with no obvious list payload: wrap as a list
                # containing itself so iteration does the right thing.
                workout_plan = [plan]
        else:
            workout_plan = []
        if not isinstance(workout_history, list):
            workout_history = []
        try:
            workout_plan = attach_to_weekly_plan(workout_plan)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in attach_to_weekly_plan: {e}", exc_info=True)
            workout_plan = []
        return (
            profile if isinstance(profile, dict) else {},
            workout_plan,
            workout_history,
            profile_id,
            "supabase",
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception in _load_user_data: {e}", exc_info=True)
        return {}, [], [], None, "unavailable"


def load_persistent_data(
    profile_file: str | Path = DATA_DIR / "profile.json",
    workout_plan_file: str | Path = DATA_DIR / "workout_plan.json",
    workout_history_file: str | Path = DATA_DIR / "workout_history.json",
    exercises_file: str | Path = DATA_DIR / "exercises.json",
    user_id: str | None = None,
    warning_callback: Callable[[str], Any] | None = None,
) -> tuple[Any, Any, Any, Any, str | None, str]:
    """Load the static catalog and authenticated user data from Supabase.

    The callback keeps Streamlit concerns at the presentation boundary while
    preserving the existing warning shown when cloud loading fails.
    """
    exercise_database = _load_exercise_catalog(exercises_file, warning_callback)

    if not user_id:
        return {}, [], [], exercise_database, None, "unavailable"

    profile, workout_plan, workout_history, profile_id, storage_source = _load_user_data(
        user_id,
        str(profile_file),
        str(workout_plan_file),
        str(workout_history_file),
    )

    if storage_source == "unavailable" and not profile:
        if storage.is_supabase_available() and warning_callback is not None:
            warning_callback(
                "Supabase is configured, but cloud data could not be loaded. "
                "Please verify the Supabase schema and credentials."
            )

    return (
        profile,
        workout_plan,
        workout_history,
        exercise_database,
        profile_id,
        storage_source if storage_source != "unavailable" else "unavailable",
    )


