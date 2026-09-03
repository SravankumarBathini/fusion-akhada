"""Server-side registration audit for the administrator dashboard."""

import logging
from datetime import datetime, timezone
from typing import Any

from config.secrets import get_secret

logger = logging.getLogger(__name__)


def _service_client() -> Any:
    from supabase import create_client

    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def registration_admin_configured() -> bool:
    """Return whether the server-only key needed by the admin view is set."""
    return bool(get_secret("SUPABASE_URL") and get_secret("SUPABASE_SERVICE_ROLE_KEY"))


def record_registration(email: str, user_id: str | None = None) -> None:
    """Record a registration for the administrator dashboard."""
    client = _service_client()
    if client is None:
        logger.warning("Registration audit skipped: service role is not configured")
        return

    client.table("registration_events").insert({
        "email": email,
        "user_id": user_id,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    logger.info("Registration recorded for administrator dashboard")


def load_registration_events() -> list[dict[str, Any]]:
    """Return tracked and historical Auth registrations for the administrator."""
    client = _service_client()
    if client is None:
        return []
    events: list[dict[str, Any]] = []
    try:
        response = (
            client.table("registration_events")
            .select("email,user_id,registered_at")
            .order("registered_at", desc=True)
            .execute()
        )
        events = response.data or []
    except Exception:
        logger.exception("Registration dashboard query failed")

    known_users = {
        str(event.get("user_id"))
        for event in events
        if event.get("user_id")
    }
    known_emails = {
        str(event.get("email", "")).strip().lower()
        for event in events
    }
    try:
        auth_users = client.auth.admin.list_users(page=1, per_page=1000)
        for user in auth_users:
            user_id = str(
                user.get("id", "") if isinstance(user, dict) else getattr(user, "id", "")
            )
            email = str(
                user.get("email", "") if isinstance(user, dict) else getattr(user, "email", "")
            ).strip().lower()
            if (user_id and user_id in known_users) or (
                email and email in known_emails
            ):
                continue
            events.append(
                {
                    "email": email,
                    "user_id": user_id or None,
                    "registered_at": (
                        user.get("created_at")
                        if isinstance(user, dict)
                        else getattr(user, "created_at", None)
                    ),
                    "source": "Historical Auth user",
                }
            )
    except Exception:
        logger.exception("Historical Auth user query failed")

    return sorted(
        events,
        key=lambda event: str(event.get("registered_at") or ""),
        reverse=True,
    )
