from __future__ import annotations

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


# ============================================================
# SUPABASE CONNECTION
# ============================================================

def _get_supabase_client() -> Client | None:
    """
    Create and return a Supabase client.

    Returns None when Supabase configuration is unavailable.
    """

    supabase_url = _get_secret(
        "SUPABASE_URL"
    )

    supabase_key = _get_secret(
        "SUPABASE_KEY"
    )

    if not supabase_url or not supabase_key or create_client is None:
        return None

    try:

        client = create_client(
            supabase_url,
            supabase_key,
        )
        if st is not None:
            auth_session = st.session_state.get("supabase_session")
            if isinstance(auth_session, dict):
                access_token = auth_session.get("access_token")
                refresh_token = auth_session.get("refresh_token")
                if access_token and refresh_token:
                    client.auth.set_session(access_token, refresh_token)
        return client

    except Exception:
        return None


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
        return
    if client.auth.get_session() is not None:
        client.auth.sign_out()


def _profiles_support_user_id(client: Client) -> bool:
    """Detect whether the deployed profiles schema has tenant ownership."""
    try:
        client.table("profiles").select("user_id").limit(1).execute()
    except Exception:
        return False
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

    except Exception:

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

    except Exception:

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

    except Exception:

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
    except Exception:
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

    except Exception:

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

    except Exception:

        return None

    if not response.data:
        return None

    return response.data[0].get(
        "id"
    )
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
    except Exception as e:
        _sidebar_message("error", f"Cloud reset error: {str(e)}")
        return False

    return True
