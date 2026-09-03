"""Application bootstrap use case for loading the active user's data."""

from pathlib import Path
from typing import Any, Callable

from config.settings import DATA_DIR
from infrastructure import storage


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

    exercise_database: list[Any] = []
    supabase_available = storage.is_supabase_available()
    if supabase_available:
        try:
            client = storage._get_supabase_client()
            if client is not None:
                response = client.table("exercises").select("*").execute()
                if response.data:
                    exercise_database = response.data
        except Exception as error:
            if warning_callback is not None:
                warning_callback(
                    "The Supabase exercise catalog could not be loaded. "
                    f"Details: {error}"
                )

    if not exercise_database:
        exercise_database = storage.load_json(exercises_file, [])

    if supabase_available and user_id and storage.supabase_schema_ready():
        try:
            profile = storage.load_latest_profile_from_supabase(user_id)
            profile_id = storage.get_latest_profile_id(user_id)
            workout_plan = (
                storage.load_latest_workout_plan_from_supabase(profile_id)
                if profile_id
                else []
            )
            workout_history = (
                storage.load_workout_history_from_supabase(profile_id)
                if profile_id
                else []
            )
            return (
                profile or {},
                workout_plan or [],
                workout_history or [],
                exercise_database,
                profile_id,
                "supabase",
            )
        except Exception as error:
            if warning_callback is not None:
                warning_callback(
                    "Supabase is configured, but cloud data could not be loaded. "
                    "Please verify the Supabase schema and credentials. "
                    f"Details: {error}"
                )

    return (
        {},
        [],
        [],
        exercise_database,
        None,
        "unavailable",
    )
