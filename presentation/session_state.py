"""Streamlit session-state initialisation at the presentation boundary."""

from collections.abc import MutableMapping
from typing import Any


DEFAULT_SESSION_STATE: dict[str, Any] = {
    "profile_created": False,
    "profile": {},
    "workout_plan": [],
    "workout_history": [],
    "page": "Dashboard",
    "cloud_data_loaded": False,
    "profile_id": None,
    "storage_source": "unavailable",
    "supabase_session": None,
}


def initialize_session_state(session_state: MutableMapping[str, Any]) -> None:
    """Populate missing session keys without overwriting an active session."""

    for key, default in DEFAULT_SESSION_STATE.items():
        if key not in session_state:
            session_state[key] = default.copy() if isinstance(default, (dict, list)) else default
