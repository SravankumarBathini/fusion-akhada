"""Backward-compatible storage facade.

The implementation lives in :mod:`infrastructure.storage`; this module keeps
all historical ``utils.storage`` imports working for Streamlit pages and users.
"""
from infrastructure.storage import (
    BASE_DIR,
    DATA_DIR,
    ENV_FILE,
    _get_secret,
    _get_supabase_client,
    _load_dotenv_file,
    get_latest_profile_id,
    is_supabase_available,
    load_json,
    load_latest_profile_from_supabase,
    load_latest_workout_plan_from_supabase,
    load_workout_history_from_supabase,
    reset_user_progress_soft,
    save_json,
    save_profile_to_supabase,
    sign_out_supabase,
    supabase_schema_ready,
    save_workout_history_to_supabase,
    save_workout_plan_to_supabase,
)

__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "ENV_FILE",
    "get_latest_profile_id",
    "is_supabase_available",
    "load_json",
    "load_latest_profile_from_supabase",
    "load_latest_workout_plan_from_supabase",
    "load_workout_history_from_supabase",
    "reset_user_progress_soft",
    "save_json",
    "save_profile_to_supabase",
    "sign_out_supabase",
    "supabase_schema_ready",
    "save_workout_history_to_supabase",
    "save_workout_plan_to_supabase",
]
