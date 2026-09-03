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
    """Return registration events for the configured administrator."""
    client = _service_client()
    if client is None:
        return []
    response = (
        client.table("registration_events")
        .select("email,user_id,registered_at")
        .order("registered_at", desc=True)
        .execute()
    )
    return response.data or []
