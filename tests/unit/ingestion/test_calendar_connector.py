"""Unit tests for GoogleCalendarConnector."""

from __future__ import annotations

import httpx
import pytest
import respx

from ingestion.connectors.google_calendar import GoogleCalendarConnector
from ingestion.models import CalendarActivityEvent
from tests.unit.ingestion.conftest import SINCE, TEAM_ID, UNTIL, WORKSPACE_ID

_ACCESS_TOKEN = "ya29.test_token"
_CALENDAR_IDS = ["primary@team.com"]

_API_BASE = "https://www.googleapis.com/calendar/v3"


def _make_connector(client: httpx.AsyncClient) -> GoogleCalendarConnector:
    return GoogleCalendarConnector(
        workspace_id=WORKSPACE_ID,
        http_client=client,
        access_token=_ACCESS_TOKEN,
        calendar_ids=_CALENDAR_IDS,
    )


def _calendar_response(items: list[dict]) -> dict:
    return {"kind": "calendar#events", "items": items}


def _event_item(start: str, end: str) -> dict:
    return {
        "kind": "calendar#event",
        # title and summary deliberately omitted — connector should not need them
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }


# ── fetch_events ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_calendar_fetch_events_returns_typed_events(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/calendars/primary@team.com/events").mock(
        return_value=httpx.Response(
            200,
            json=_calendar_response(
                [
                    _event_item("2024-01-15T10:00:00+00:00", "2024-01-15T11:00:00+00:00"),
                    _event_item("2024-01-15T14:00:00+00:00", "2024-01-15T15:00:00+00:00"),
                ]
            ),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert len(events) == 1  # both meetings on the same day → one CalendarActivityEvent
    assert isinstance(events[0], CalendarActivityEvent)
    assert events[0].date_utc == "2024-01-15"
    assert events[0].meeting_count == 2
    assert events[0].total_meeting_minutes == 120


@pytest.mark.asyncio
@respx.mock
async def test_calendar_fetch_events_detects_back_to_back(
    async_http_client: httpx.AsyncClient,
) -> None:
    # 3-minute gap between meetings → back-to-back
    respx.get(f"{_API_BASE}/calendars/primary@team.com/events").mock(
        return_value=httpx.Response(
            200,
            json=_calendar_response(
                [
                    _event_item("2024-01-15T10:00:00+00:00", "2024-01-15T11:00:00+00:00"),
                    _event_item("2024-01-15T11:03:00+00:00", "2024-01-15T12:00:00+00:00"),
                    _event_item("2024-01-15T14:00:00+00:00", "2024-01-15T15:00:00+00:00"),
                ]
            ),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert events[0].back_to_back_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_calendar_fetch_events_counts_after_hours_minutes(
    async_http_client: httpx.AsyncClient,
) -> None:
    # Meeting 19:00-20:00 → 60 after-hours minutes
    respx.get(f"{_API_BASE}/calendars/primary@team.com/events").mock(
        return_value=httpx.Response(
            200,
            json=_calendar_response(
                [_event_item("2024-01-15T19:00:00+00:00", "2024-01-15T20:00:00+00:00")]
            ),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert events[0].after_hours_meeting_minutes == 60


@pytest.mark.asyncio
@respx.mock
async def test_calendar_fetch_events_no_attendee_names_in_output(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/calendars/primary@team.com/events").mock(
        return_value=httpx.Response(
            200,
            json=_calendar_response(
                [
                    {
                        "kind": "calendar#event",
                        "summary": "SECRET MEETING NAME",
                        "start": {"dateTime": "2024-01-15T10:00:00+00:00"},
                        "end": {"dateTime": "2024-01-15T11:00:00+00:00"},
                        "attendees": [{"email": "person@org.com", "displayName": "Alice"}],
                    }
                ]
            ),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    serialized = events[0].model_dump_json()
    assert "SECRET" not in serialized
    assert "Alice" not in serialized
    assert "person@org.com" not in serialized


@pytest.mark.asyncio
@respx.mock
async def test_calendar_fetch_events_empty_on_http_error(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/calendars/primary@team.com/events").mock(
        return_value=httpx.Response(403)
    )
    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)
    assert events == []
