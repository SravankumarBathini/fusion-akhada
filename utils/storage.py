import json
import os
from pathlib import Path
from typing import Any

import streamlit as st
from supabase import Client, create_client


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"


# ============================================================
# LOCAL .ENV LOADER
# ============================================================

def _load_dotenv_file() -> dict[str, str]:
    """
    Read simple KEY=VALUE pairs from the project's .env file.

    This avoids requiring an additional dotenv dependency.
    """

    values: dict[str, str] = {}

    if not ENV_FILE.exists():
        return values

    try:

        with ENV_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            for raw_line in file:

                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split(
                    "=",
                    1,
                )

                key = key.strip()
                value = value.strip()

                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in {"'", '"'}
                ):

                    value = value[1:-1]

                values[key] = value

    except OSError:
        pass

    return values


# ============================================================
# CONFIGURATION VALUE
# ============================================================

def _get_secret(
    name: str,
) -> str | None:
    """
    Read a configuration value in this order:

    1. Streamlit Secrets
    2. Local .env file
    3. Environment variables
    """

    # --------------------------------------------------------
    # 1. Streamlit Secrets
    # --------------------------------------------------------

    try:

        value = st.secrets.get(name)

        if value:
            return str(value)

    except Exception:
        pass

    # --------------------------------------------------------
    # 2. Local .env
    # --------------------------------------------------------

    dotenv_values = _load_dotenv_file()

    value = dotenv_values.get(name)

    if value:
        return value

    # --------------------------------------------------------
    # 3. Environment variables
    # --------------------------------------------------------

    value = os.getenv(name)

    if value:
        return value

    return None


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

    if not supabase_url or not supabase_key:
        return None

    try:

        return create_client(
            supabase_url,
            supabase_key,
        )

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


# ============================================================
# LOCAL JSON STORAGE
# ============================================================

def load_json(
    file_path: str | Path,
    default: Any = None,
) -> Any:
    """
    Load JSON data from a local file.

    Local JSON remains available for:

    - local development
    - fallback behavior
    - reference data
    - debugging
    """

    path = Path(file_path)

    if not path.exists():
        return default

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return default


def save_json(
    file_path: str | Path,
    data: Any,
) -> bool:
    """
    Save JSON data to a local file.

    Returns True on success and False on failure.
    """

    path = Path(file_path)

    try:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        return True

    except OSError:

        return False


# ============================================================
# SUPABASE PROFILE STORAGE
# ============================================================

def save_profile_to_supabase(
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Save a profile to Supabase.

    The complete original profile dictionary is preserved
    inside profile_data JSONB.

    Returns the inserted row on success.
    Returns None when Supabase is unavailable or the insert
    does not return a row.
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

    try:

        response = (
            client
            .table("profiles")
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


def load_latest_profile_from_supabase() -> dict[str, Any] | None:
    """
    Load the most recently created profile from Supabase.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    try:

        response = (
            client
            .table("profiles")
            .select("*")
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

    The complete original workout object is preserved
    inside workout_data JSONB.

    Returns:
        The inserted Supabase row on success.
        None when Supabase is unavailable or the insert fails.
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

    except Exception:

        return None

    # IMPORTANT:
    # Only report success when Supabase actually
    # returned the inserted row.
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

def get_latest_profile_id() -> str | None:
    """
    Return the UUID of the latest profile in Supabase.
    """

    client = _get_supabase_client()

    if client is None:
        return None

    try:

        response = (
            client
            .table("profiles")
            .select("id")
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

    return response.data[0].get(
        "id"
    )
# ============================================================
# PROGRESS RESET UTILITY (SOFT RESET)
# ============================================================

def reset_user_progress_soft() -> bool:
    import streamlit as st
    from utils.storage import DATA_DIR, _get_supabase_client, get_latest_profile_id
    
    local_files = ["workout_plan.json", "workout_history.json"]
    for f in local_files:
        path = DATA_DIR / f
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
                
    client = _get_supabase_client()
    if client is not None:
        try:
            pid = get_latest_profile_id()
            if pid:
                client.table("workout_history").delete().eq("profile_id", pid).execute()
                client.table("workout_plans").delete().eq("profile_id", pid).execute()
            else:
                client.table("workout_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                client.table("workout_plans").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            st.sidebar.error(f"Cloud reset error: {str(e)}")
            return False
            
    return True
