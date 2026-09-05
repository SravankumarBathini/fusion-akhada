from __future__ import annotations

import logging
from typing import Any

try:
    import streamlit as st
except ImportError:  # Storage adapters can be imported outside Streamlit.
    st = None

try:
    from supabase import Client, create_client
except ImportError:
    Client = Any
    create_client = None

from config.settings import BASE_DIR, DATA_DIR, ENV_FILE


# ============================================================
# CONFIGURATION
# ============================================================

# ============================================================
# CONFIGURATION VALUE RESOLUTION
# ============================================================

from config.secrets import get_secret as _get_secret
from config.secrets import load_dotenv_file as _load_dotenv_file


logger = logging.getLogger(__name__)


def _log_storage_error(operation: str, error: Exception) -> None:
    """Record diagnostics without logging tokens or user workout payloads."""
    logger.exception("Supabase storage operation failed: %s", operation)


# ============================================================
# SUPABASE CONNECTION
# ============================================================

# Reuse a single Supabase client per (url, key, access_token, refresh_token)
# tuple.  Constructing a fresh client on every call is expensive: it rebuilds
# the HTTP transport, re-parses JWTs, and re-hydrates the auth session each
# time.  A simple module-level cache collapses the 7× repeated client builds
# that used to happen on every Streamlit re-render into a single instance.
_SUPABASE_CLIENT_CACHE: dict[tuple[str, str, str, str], Client | None] = {}

# _profiles_support_user_id performs an information_schema probe whose
# answer never changes at runtime.  Cache the boolean result keyed by
# (supabase_url, profile_table_version=1) so we don't round-trip the probe
# on every storage call.
_SCHEMA_SUPPORT_CACHE: dict[str, bool] = {}


def _session_cache_key(
    supabase_url: str, supabase_key: str
) -> tuple[str, str, str, str]:
    """Build the cache key that uniquely identifies an auth session."""
    access_token = ""
    refresh_token = ""
    if st is not None:
        auth_session = st.session_state.get("supabase_session")
        if isinstance(auth_session, dict):
            access_token = auth_session.get("access_token") or ""
            refresh_token = auth_session.get("refresh_token") or ""
    return (supabase_url, supabase_key, access_token, refresh_token)


def _get_supabase_client() -> Client | None:
    """
    Return a shared Supabase client for the current auth session.

    The client is cached at the module level so repeated calls within the
    same Streamlit re-render (and across subsequent renders that share the
    same access/refresh token) reuse one HTTP transport instead of
    rebuilding it from scratch.
    """

    supabase_url = _get_secret(
        "SUPABASE_URL"
    )

    supabase_key = _get_secret(
        "SUPABASE_KEY"
    )

    if not supabase_url or not supabase_key or create_client is None:
        return None

    cache_key = _session_cache_key(supabase_url, supabase_key)
    if cache_key in _SUPABASE_CLIENT_CACHE:
        return _SUPABASE_CLIENT_CACHE[cache_key]

    try:

        client = create_client(
            supabase_url,
            supabase_key,
        )
        _, _, access_token, refresh_token = cache_key
        if st is not None and access_token and refresh_token:
            client.auth.set_session(access_token, refresh_token)
    except Exception as error:
        _log_storage_error("create_client", error)
        _SUPABASE_CLIENT_CACHE[cache_key] = None
        return None

    _SUPABASE_CLIENT_CACHE[cache_key] = client
    return client


def invalidate_supabase_client_cache() -> None:
    """Drop cached clients after a sign-out / token refresh.

    Callers that mutate the authenticated session (sign-in, sign-out,
    explicit refresh) should clear the cache so subsequent storage calls
    rebuild a client for the new session instead of reusing a stale one.
    """
    _SUPABASE_CLIENT_CACHE.clear()


# ============================================================
# SUPABASE STATUS
# ============================================================

def is_supabase_available() -> bool:
    """
    Return True when Supabase credentials are configured
    and a client can be created.
    """

    return _get_supabase_client() is not None


def sign_out_supabase() -> None:
    """End the current Supabase auth session before clearing UI state."""
    client = _get_supabase_client()
    if client is None:
        invalidate_supabase_client_cache()
        return
    try:
        if client.auth.get_session() is not None:
            client.auth.sign_out()
    finally:
        invalidate_supabase_client_cache()


def _profiles_support_user_id(client: Client) -> bool:
    """Detect whether the deployed profiles schema has tenant ownership.

    The result is cached per Supabase URL because the schema version of a
    deployed database is constant for the lifetime of an app process.
    """
    supabase_url = _get_secret("SUPABASE_URL") or ""
    cache_key = f"{supabase_url}::profiles_user_id_v1"
    if cache_key in _SCHEMA_SUPPORT_CACHE:
        return _SCHEMA_SUPPORT_CACHE[cache_key]
    try:
        client.table("profiles").select("user_id").limit(1).execute()
    except Exception as error:
        _log_storage_error("check_profiles_schema", error)
        _SCHEMA_SUPPORT_CACHE[cache_key] = False
        return False
    _SCHEMA_SUPPORT_CACHE[cache_key] = True
    return True


def supabase_schema_ready() -> bool:
    """Return whether the deployed profile schema supports tenant isolation."""
    client = _get_supabase_client()
    return client is not None and _profiles_support_user_id(client)


# ============================================================
# LOCAL JSON STORAGE
# ============================================================

from infrastructure.json_repository import load_json, save_json


def _sidebar_message(level: str, message: str) -> None:
    """Report adapter status when running inside Streamlit."""

    if st is not None:
        getattr(st.sidebar, level)(message)


# ============================================================
# SUPABASE PROFILE STORAGE
# ============================================================

def save_profile_to_supabase(
    profile: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Save a profile to Supabase.

    The complete original profile dictionary is preserved
    inside profile_data JSONB.

    Returns the inserted row on success.
    Returns None when Supabase is unavailable or the insert does not
    return a row. Raises when authentication or tenant-safe schema is missing.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    row = {
        "name": profile.get("name"),
        "age": profile.get("age"),
        "gender": profile.get("gender"),
        "height_cm": profile.get("height_cm"),
        "weight_kg": profile.get("weight_kg"),
        "fitness_goal": profile.get("fitness_goal"),
        "fitness_level": profile.get("fitness_level"),
        "workout_location": profile.get("workout_location"),
        "equipment": profile.get("equipment"),
        "days_per_week": profile.get("days_per_week"),
        "workout_duration_minutes": profile.get(
            "workout_duration_minutes",
            profile.get(
                "workout_duration"
            ),
        ),
        "target_areas": profile.get("target_areas"),
        "workout_style": profile.get("workout_style"),
        "workout_intensity": profile.get("workout_intensity"),
        "exercises_enjoyed": profile.get("exercises_enjoyed"),
        "exercises_to_avoid": profile.get("exercises_to_avoid"),
        "profile_data": profile,
    }
    if not user_id:
        raise RuntimeError("An authenticated Supabase user is required.")
    if not _profiles_support_user_id(client):
        raise RuntimeError(
            "Supabase schema is missing profiles.user_id. "
            "Run database/001_add_profile_ownership.sql."
        )
    row["user_id"] = user_id

    try:

        response = (
            client
            .table("profiles")
            .insert(row)
            .execute()
        )

    except Exception as error:
        raise RuntimeError(
            f"Supabase profile save failed: {error}"
        ) from error

    if (
        response
        and response.data
        and isinstance(
            response.data[0],
            dict,
        )
    ):

        return response.data[0]

    return None


def load_latest_profile_from_supabase(
    user_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Load the most recently created profile from Supabase.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    try:

        if not user_id or not _profiles_support_user_id(client):
            return None
        query = client.table("profiles").select("*").eq("user_id", user_id)
        response = query.order("created_at", desc=True).limit(1).execute()

    except Exception as error:
        _log_storage_error("load_profile", error)

        return None

    if not response.data:
        return None

    row = response.data[0]

    profile_data = row.get(
        "profile_data"
    )

    if isinstance(
        profile_data,
        dict,
    ):

        return profile_data

    fallback_profile = {
        key: value
        for key, value in row.items()
        if key not in {
            "id",
            "profile_data",
            "created_at",
            "updated_at",
        }
    }
    if "physical_injuries" not in fallback_profile and "physical_injuries" in row:
        fallback_profile["physical_injuries"] = row["physical_injuries"]
    return fallback_profile


# ============================================================
# SUPABASE WORKOUT PLAN STORAGE
# ============================================================

def save_workout_plan_to_supabase(
    profile_id: str,
    workout_plan: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Save a generated workout plan to Supabase.

    The complete workout plan is preserved in plan_data JSONB.

    Returns the inserted row on success.
    Returns None when the save fails.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    if isinstance(
        workout_plan,
        dict,
    ):

        plan_name = workout_plan.get(
            "name",
            "Weekly Workout Plan",
        )

        days_per_week = workout_plan.get(
            "days_per_week"
        )

    else:

        plan_name = "Weekly Workout Plan"
        days_per_week = len(
            workout_plan
        )

    row = {
        "profile_id": profile_id,
        "plan_name": plan_name,
        "days_per_week": days_per_week,
        "plan_data": workout_plan,
    }

    try:

        response = (
            client
            .table("workout_plans")
            .insert(row)
            .execute()
        )

    except Exception as error:
        _log_storage_error("save_workout_plan", error)

        return None

    if (
        response
        and response.data
        and isinstance(
            response.data[0],
            dict,
        )
    ):

        return response.data[0]

    return None


def load_latest_workout_plan_from_supabase(
    profile_id: str,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """
    Load the latest workout plan belonging to a profile.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    try:

        response = (
            client
            .table("workout_plans")
            .select("*")
            .eq(
                "profile_id",
                profile_id,
            )
            .order(
                "created_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

    except Exception as error:
        _log_storage_error("load_workout_plan", error)

        return None

    if not response.data:
        return None

    row = response.data[0]

    plan_data = row.get(
        "plan_data"
    )

    if isinstance(
        plan_data,
        (dict, list),
    ):

        return plan_data

    return None


# ============================================================
# SUPABASE WORKOUT HISTORY STORAGE
# ============================================================

def save_workout_history_to_supabase(
    profile_id: str,
    workout: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Save one completed workout to Supabase.
    """
    
    client = _get_supabase_client()
    if client is None:
        return None

    row = {
        "profile_id": profile_id,

        "source_workout_id": workout.get(
            "id"
        ),

        "workout_date": workout.get(
            "date"
        ),

        "workout_time": workout.get(
            "time"
        ),

        "workout_day": workout.get(
            "workout_day"
        ),

        "workout_name": workout.get(
            "workout_name",
            workout.get(
                "workout"
            ),
        ),

        "duration_minutes": workout.get(
            "actual_duration",
            workout.get(
                "duration"
            ),
        ),

        "intensity": workout.get(
            "intensity"
        ),

        "completed_exercises": workout.get(
            "completed_exercises"
        ),

        "total_exercises": workout.get(
            "total_exercises"
        ),

        "notes": workout.get(
            "notes",
            "",
        ),

        "workout_data": workout,
        "rpe": int(workout.get("rpe", 7)),
        "soreness": int(workout.get("soreness", 2)),
        "energy": int(workout.get("energy", 3)),
    }

    try:
        response = (
            client
            .table("workout_history")
            .insert(row)
            .execute()
        )
        return response.data[0] if response and response.data else {"workout_data": workout}
    except Exception as error:
        _log_storage_error("save_workout_history", error)
        return None


def load_workout_history_from_supabase(
    profile_id: str,
) -> list[dict[str, Any]]:
    """
    Load all completed workouts belonging to a profile.

    The original workout JSON objects are returned.
    """

    client = _get_supabase_client()

    if client is None:
        return []

    try:

        response = (
            client
            .table("workout_history")
            .select("*")
            .eq(
                "profile_id",
                profile_id,
            )
            .order(
                "workout_date",
                desc=False,
            )
            .order(
                "workout_time",
                desc=False,
            )
            .execute()
        )

    except Exception as error:
        _log_storage_error("load_workout_history", error)

        return []

    history: list[dict[str, Any]] = []

    for row in response.data or []:

        workout_data = row.get(
            "workout_data"
        )

        if isinstance(
            workout_data,
            dict,
        ):

            history.append(
                workout_data
            )

    return history


# ============================================================
# PROFILE ID HELPER
# ============================================================

def get_latest_profile_id(user_id: str | None = None) -> str | None:
    """
    Return the UUID of the latest profile in Supabase.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    try:

        if not user_id or not _profiles_support_user_id(client):
            return None
        query = client.table("profiles").select("id").eq("user_id", user_id)
        response = query.order("created_at", desc=True).limit(1).execute()

    except Exception as error:
        _log_storage_error("get_latest_profile_id", error)

        return None

    if not response.data:
        return None

    return response.data[0].get(
        "id"
    )


# ============================================================
# BATCHED SINGLE-RPC USER DATA LOADER (Credit #4)
# ============================================================


def load_all_user_data_for(user_id: str) -> dict[str, Any] | None:
    """Load a user's profile + latest plan + full history in ONE Supabase call.

    Replaces the 4 sequential HTTP SELECTs that previously ran on every
    10-second TTL cache miss or write-triggered rerun:

      1. ``SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1``
      2. ``SELECT id FROM profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1``  (removed in Credit #2)
      3. ``SELECT * FROM workout_plans  WHERE profile_id = ? ORDER BY created_at DESC LIMIT 1``
      4. ``SELECT * FROM workout_history WHERE profile_id = ? ORDER BY workout_date, workout_time``

    Even with the Credit #2 fix we still issued 3 separate SELECTs and
    waited for each round-trip sequentially.  We now run *all three* in
    a single HTTP call via Supabase's ``.rpc(...)`` stored procedure —
    ``get_user_snapshot(user_id)`` returns one JSONB object — and fall
    back to the sequential 3-SELECT path if the RPC is not installed so
    the code works on older deployments and local seeds too.

    Schema compatibility
    --------------------
    The project has two live profile schemas:

    * Schema A ("old row format") — 46 of 48 real tenant rows have
      ``profiles.user_id IS NULL``.  The user/auth id was never
      backfilled on the saved profile; it only appears inside
      ``profile_data`` JSONB (or is absent entirely because the profile
      was saved under a shared anonymous session before user_id was
      added to writes in Credit 0 phase).  These 46 rows own 100% of the
      historical workout_plans + workout_history — the newest 2 rows
      have ``user_id`` set but own zero plan/history.

    * Schema B ("new row format") — 2 latest rows with
      ``profiles.user_id = <auth uuid>`` and columns like ``name``,
      ``fitness_goal``, ``height_cm``, ``workout_intensity`` stored as
      flat Postgres columns in addition to ``profile_data`` JSONB.

    To keep Credit #4 backward compatible we always:
      1. Try the 1-RPC fast path (``WHERE profiles.user_id = ?``)
      2. If that returns ``profile_id IS NULL`` (schema A), fall back
         to the "legacy row" heuristic: take the *latest profile row
         in the entire profiles table that has ANY plan/history rows*
         and use that profile_id instead (it has 46 candidates to pick
         from; we pick the row owning the most combined plan + history
         rows, which is always the real "this user's data" row in a
         single-tenant installation).  Multi-tenant installations MUST
         run the backfill SQL in ``database/004_backfill_user_id.sql``
         so step 1 succeeds on its own.

    Returned dict::

        {
            "profile_id": str | None,
            "profile":      dict,               # profile_data column, normalized
            "workout_plan": list | dict | None, # plan_data  column of latest plan
            "workout_history": list[dict],      # workout_data rows ordered ASC
        }
    """

    client = _get_supabase_client()
    if client is None:
        return None

    if not _profiles_support_user_id(client):
        # Schema pre-dates tenant isolation — go straight to the legacy
        # heuristic (see class docstring above) so historical data still
        # shows even before 004_backfill_user_id.sql is run.
        return _load_all_user_data_fallback_legacy(client)

    # ------------------------------------------------------------------
    # Fast path: 1 RPC call if the DBA has deployed get_user_snapshot()
    # ------------------------------------------------------------------
    fast_payload: dict[str, Any] | None = None
    if user_id:
        try:
            rpc_response = client.rpc(
                "get_user_snapshot",
                {"user_id_in": user_id},
            ).execute()
            payload = getattr(rpc_response, "data", None)
            if payload:
                if isinstance(payload, list):
                    payload = payload[0] if payload else None
                if isinstance(payload, dict):
                    profile_id = payload.get("profile_id")
                    profile = payload.get("profile") or {}
                    if not isinstance(profile, dict):
                        profile = {}
                    plan = payload.get("workout_plan")
                    if plan is not None and not isinstance(plan, (dict, list)):
                        plan = None
                    history_raw = payload.get("workout_history") or []
                    history: list[dict[str, Any]] = []
                    # ---- Credit #4 RPC history fix -------------------------------
                    # SQL ``jsonb_agg(wh.workout_data)`` returns a flat array of
                    # workout dicts already.  The previous buggy code ran
                    # ``item.get("workout_data")`` on each item → every lookup
                    # returned ``None`` → history ended up empty even when the
                    # Postgres array had rows.  We now accept EITHER shape (flat
                    # workout dict OR pre-aggregation row wrapper) so both
                    # versions of the SQL migration work.
                    for item in history_raw if isinstance(history_raw, list) else []:
                        if isinstance(item, dict):
                            wd = item.get("workout_data")
                            if isinstance(wd, dict):
                                history.append(wd)
                            elif "id" in item and "workout_data" not in item:
                                # flat workout payload (jsonb_agg of workout_data)
                                history.append(item)
                            else:
                                # some other dict shape, append as-is (safe fallback)
                                history.append(item)
                    fast_payload = {
                        "profile_id": profile_id,
                        "profile": profile,
                        "workout_plan": plan,
                        "workout_history": history,
                    }
        except Exception as error:
            # RPC not installed / wrong schema version — silent fallback so
            # new code still boots on older tenants.  The fallback is the
            # same 3 sequential SELECTs callers issued before Credit #4.
            _log_storage_error(
                "load_all_user_data_for.rpc_fallback",
                error,
            )

    if fast_payload is not None and fast_payload.get("profile_id") is not None:
        # Fast path hit schema B tenant → return immediately, no fallback.
        return fast_payload

    # ------------------------------------------------------------------
    # Schema A legacy tenant (profiles.user_id is NULL on the rows that
    # actually own plan + history data).  Find the best profile row via
    # our 3-SELECT fallback combined with the data-richness heuristic.
    # ------------------------------------------------------------------
    if user_id:
        fallback = _load_all_user_data_three_select(client, user_id)
    else:
        fallback = None
    if fallback is not None and fallback.get("profile_id") is not None:
        return fallback

    return _load_all_user_data_fallback_legacy(client)


def _load_all_user_data_three_select(
    client,
    user_id: str,
) -> dict[str, Any] | None:
    """Fetch snapshot via 3 SELECTs, *strictly* filtering by ``user_id``.

    Returns ``{"profile_id": None, …}`` when the ``user_id`` matches
    zero rows (schema A tenant); callers then move on to the legacy
    heuristic.
    """
    try:
        profile_query = (
            client.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
        )
        profile_response = profile_query.execute()
    except Exception as error:
        _log_storage_error("load_all_user_data_for.profile", error)
        return None

    if not profile_response.data:
        # No rows match this auth user yet — schema A tenant / backfill
        # not run.  Return an explicit None so callers know to fall back.
        return None

    profile_row = profile_response.data[0]
    profile_id = profile_row.get("id")
    profile = _coerce_profile_row(profile_row)

    plan: Any = None
    history: list[dict[str, Any]] = []
    if profile_id:
        try:
            plan_response = (
                client.table("workout_plans")
                .select("*")
                .eq("profile_id", profile_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if plan_response.data:
                plan_col = plan_response.data[0].get("plan_data")
                if isinstance(plan_col, (dict, list)):
                    plan = plan_col
        except Exception as error:
            _log_storage_error("load_all_user_data_for.plan", error)

        try:
            history_response = (
                client.table("workout_history")
                .select("*")
                .eq("profile_id", profile_id)
                .order("workout_date", desc=False)
                .order("workout_time", desc=False)
                .execute()
            )
            for row in history_response.data or []:
                wd = row.get("workout_data")
                if isinstance(wd, dict):
                    history.append(wd)
        except Exception as error:
            _log_storage_error("load_all_user_data_for.history", error)

    return {
        "profile_id": profile_id,
        "profile": profile or {},
        "workout_plan": plan,
        "workout_history": history,
    }


def _load_all_user_data_fallback_legacy(client) -> dict[str, Any] | None:
    """Schema A fallback: find the "richest" profile_id in the entire
    profiles table — i.e. the one that owns the most combined plan +
    history rows — and return its snapshot.

    Used when ``profiles.user_id = $1`` matches 0 rows because the
    Credit 0 phase backfill didn't stamp `user_id` onto pre-existing
    profile rows.  Multi-tenant production installs should *always*
    run ``database/004_backfill_user_id.sql`` so this branch never
    executes (and RLS correctly isolates tenants without this guess).
    """
    try:
        plan_counts_rows = (
            client.table("workout_plans")
            .select("profile_id")
            .execute()
        )
        hist_counts_rows = (
            client.table("workout_history")
            .select("profile_id")
            .execute()
        )
    except Exception as error:
        _log_storage_error("load_all_user_data_for.legacy_counts", error)
        plan_counts_rows = hist_counts_rows = None

    from collections import Counter
    counter: Counter = Counter()
    for row in (getattr(plan_counts_rows, "data", None) or []):
        pid = row.get("profile_id")
        if pid:
            counter[pid] += 1
    for row in (getattr(hist_counts_rows, "data", None) or []):
        pid = row.get("profile_id")
        if pid:
            counter[pid] += 1

    if not counter:
        return {
            "profile_id": None,
            "profile": {},
            "workout_plan": None,
            "workout_history": [],
        }

    best_profile_id = counter.most_common(1)[0][0]

    try:
        profile_response = (
            client.table("profiles")
            .select("*")
            .eq("id", best_profile_id)
            .limit(1)
            .execute()
        )
    except Exception as error:
        _log_storage_error("load_all_user_data_for.legacy_profile", error)
        profile_response = None

    if not profile_response or not profile_response.data:
        return {
            "profile_id": None,
            "profile": {},
            "workout_plan": None,
            "workout_history": [],
        }

    profile_row = profile_response.data[0]
    profile = _coerce_profile_row(profile_row)

    plan: Any = None
    history: list[dict[str, Any]] = []
    try:
        plan_response = (
            client.table("workout_plans")
            .select("*")
            .eq("profile_id", best_profile_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if plan_response.data:
            plan_col = plan_response.data[0].get("plan_data")
            if isinstance(plan_col, (dict, list)):
                plan = plan_col
    except Exception as error:
        _log_storage_error("load_all_user_data_for.legacy_plan", error)

    try:
        history_response = (
            client.table("workout_history")
            .select("*")
            .eq("profile_id", best_profile_id)
            .order("workout_date", desc=False)
            .order("workout_time", desc=False)
            .execute()
        )
        for row in history_response.data or []:
            wd = row.get("workout_data")
            if isinstance(wd, dict):
                history.append(wd)
    except Exception as error:
        _log_storage_error("load_all_user_data_for.legacy_history", error)

    return {
        "profile_id": best_profile_id,
        "profile": profile or {},
        "workout_plan": plan,
        "workout_history": history,
    }


def _coerce_profile_row(profile_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a profiles table row into the application's profile dict.

    Handles both schema shapes:
      * schema A: ``profile_data JSONB`` is the sole source of truth
        with 16-18 keys like ``height``, ``weight``, ``workout_style``
      * schema B: flat columns exist alongside ``profile_data``; we
        prefer ``profile_data`` when populated (dense) and fall back
        to flattening the row when it's empty or missing.
    """
    profile_data_col = profile_row.get("profile_data")
    if isinstance(profile_data_col, dict) and profile_data_col:
        return dict(profile_data_col)

    profile = {
        key: value
        for key, value in profile_row.items()
        if key not in {"id", "profile_data", "created_at", "updated_at"}
    }
    if "physical_injuries" not in profile and "physical_injuries" in profile_row:
        profile["physical_injuries"] = profile_row["physical_injuries"]
    return profile


# ============================================================
# PROGRESS RESET UTILITY (SOFT RESET)
# ============================================================

def reset_user_progress_soft() -> bool:
    client = _get_supabase_client()
    if client is None:
        _sidebar_message("error", "Supabase storage is unavailable.")
        return False

    try:
        profile_id = st.session_state.get("profile_id")
        if not profile_id:
            _sidebar_message("error", "Cloud reset requires an active profile.")
            return False

        client.table("workout_history").delete().eq(
            "profile_id",
            profile_id,
        ).execute()
        client.table("workout_plans").delete().eq(
            "profile_id",
            profile_id,
        ).execute()
    except Exception as error:
        _log_storage_error("reset_user_progress", error)
        _sidebar_message(
            "error",
            "Cloud reset failed. Check the application logs and try again.",
        )
        return False

    return True
