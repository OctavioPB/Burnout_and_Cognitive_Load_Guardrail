"""Google Calendar integration adapter.

In production: uses the Google Calendar API (service account with domain-wide
delegation) to create a recurring "Meeting-Free Friday" all-day block.

In staging (GOOGLE_CALENDAR_CREDENTIALS not set): logs the intended action and
returns a simulated success result so the rest of the workflow executes.

Environment variables:
  GOOGLE_CALENDAR_CREDENTIALS  Path to service account JSON key file
  GOOGLE_CALENDAR_DOMAIN       Workspace domain (e.g. acme.com)
"""

from __future__ import annotations

import logging
import os
import uuid

import httpx

from api.schemas.interventions import IntegrationResult

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_API_BASE = "https://www.googleapis.com/calendar/v3"


async def create_meeting_free_friday(
    team_id: str,
    team_name: str,
    actor_email: str,
) -> IntegrationResult:
    """Create a 4-week recurring all-day Meeting-Free Friday block.

    Returns:
        IntegrationResult with the created calendar event ID on success.
    """
    credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")

    if not credentials_path:
        logger.warning(
            "[STAGING] Google Calendar credentials not set — simulating "
            "Meeting-Free Friday block for team %s by %s", team_id, actor_email
        )
        return IntegrationResult(
            integration="google_calendar",
            status="success",
            external_id=f"staging-cal-{uuid.uuid4().hex[:8]}",
            detail="Staging simulation — no real calendar event created.",
        )

    # Production path: exchange service account creds for an access token,
    # then POST the recurring event.
    try:
        token = await _get_access_token(credentials_path)
        event_id = await _create_event(token, team_name, actor_email)
        logger.info("Google Calendar event created: %s for team %s", event_id, team_id)
        return IntegrationResult(
            integration="google_calendar",
            status="success",
            external_id=event_id,
            detail=f"Recurring Meeting-Free Friday block created (event {event_id}).",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Google Calendar error for team %s: %s", team_id, exc)
        return IntegrationResult(
            integration="google_calendar",
            status="failed",
            detail=str(exc),
        )


async def _get_access_token(credentials_path: str) -> str:
    """Exchange service account JSON key for a short-lived access token."""
    import json
    import time

    import jwt as pyjwt  # PyJWT

    with open(credentials_path) as f:
        creds = json.load(f)

    now = int(time.time())
    claim = {
        "iss":   creds["client_email"],
        "scope": " ".join(_SCOPES),
        "aud":   "https://oauth2.googleapis.com/token",
        "iat":   now,
        "exp":   now + 3600,
    }
    signed = pyjwt.encode(claim, creds["private_key"], algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": signed},
        )
        resp.raise_for_status()
        return str(resp.json()["access_token"])


async def _create_event(token: str, team_name: str, actor_email: str) -> str:
    """POST a 4-week recurring FRIDAY all-day event; return its event ID."""
    from datetime import date, timedelta

    today = date.today()
    # Find next Friday
    days_until_friday = (4 - today.weekday()) % 7 or 7
    first_friday = today + timedelta(days=days_until_friday)

    event = {
        "summary": f"🚫 Meeting-Free Friday — {team_name}",
        "description": "Burnout Guardrail: deep-work protection block. No recurring meetings.",
        "start": {"date": first_friday.isoformat()},
        "end":   {"date": first_friday.isoformat()},
        "recurrence": ["RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=FR"],
        "organizer": {"email": actor_email},
        "status": "confirmed",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_API_BASE}/calendars/primary/events",
            json=event,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return str(resp.json()["id"])
