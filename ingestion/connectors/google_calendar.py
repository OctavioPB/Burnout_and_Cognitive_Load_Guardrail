"""Google Calendar connector — team meeting-load metadata."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.models import CalendarActivityEvent

logger = logging.getLogger(__name__)

_API_BASE = "https://www.googleapis.com/calendar/v3"
_BACK_TO_BACK_GAP_MINUTES = 5
_WORK_HOURS_START = 9   # 09:00 local time (UTC approximation)
_WORK_HOURS_END = 18    # 18:00 local time
_PAGE_SIZE = 250


class GoogleCalendarConnector(BaseConnector[CalendarActivityEvent]):
    """Fetches meeting metadata from the Google Calendar API.

    Captures: event start time, end time, and count.
    Does NOT capture: event title, description, attendee names, or organizer.

    Args:
        workspace_id: Google Workspace customer ID.
        http_client:  Injected httpx.AsyncClient.
        access_token: OAuth2 access token for the service account.
        calendar_ids: Calendar IDs to aggregate for this team.
    """

    def __init__(
        self,
        workspace_id: str,
        http_client: httpx.AsyncClient,
        access_token: str,
        calendar_ids: list[str],
    ) -> None:
        super().__init__(workspace_id=workspace_id, http_client=http_client)
        self._calendar_ids = calendar_ids
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def fetch_events(
        self,
        team_id: str,
        since: datetime,
        until: datetime,
    ) -> list[CalendarActivityEvent]:
        # Collect all (start, end) pairs for the window, then aggregate per date
        meetings: list[tuple[datetime, datetime]] = []
        for calendar_id in self._calendar_ids:
            meetings.extend(await self._fetch_meeting_windows(calendar_id, since, until))

        return self._aggregate_by_day(team_id, meetings)

    async def health_check(self) -> bool:
        try:
            response = await self._http.get(
                f"{_API_BASE}/users/me/calendarList",
                headers=self._headers,
                timeout=10.0,
            )
            return response.status_code == 200
        except httpx.HTTPError as exc:
            self._logger.warning("Google Calendar health check failed: %s", exc)
            return False

    async def _fetch_meeting_windows(
        self,
        calendar_id: str,
        since: datetime,
        until: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """Return (start, end) pairs. No event title or attendees are stored."""
        windows: list[tuple[datetime, datetime]] = []
        page_token: str | None = None

        while True:
            params: dict[str, str | int] = {
                "timeMin": since.isoformat(),
                "timeMax": until.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": _PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                response = await self._http.get(
                    f"{_API_BASE}/calendars/{calendar_id}/events",
                    headers=self._headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "Google Calendar API HTTP %d for calendar %s",
                    exc.response.status_code,
                    calendar_id,
                )
                break

            data: dict[str, Any] = response.json()
            for item in data.get("items", []):
                start_raw = (item.get("start") or {}).get("dateTime")
                end_raw = (item.get("end") or {}).get("dateTime")
                if start_raw and end_raw:
                    start = datetime.fromisoformat(start_raw)
                    end = datetime.fromisoformat(end_raw)
                    if end > start:
                        windows.append((start, end))

            page_token = data.get("nextPageToken") or None
            if not page_token:
                break

        return windows

    def _aggregate_by_day(
        self,
        team_id: str,
        meetings: list[tuple[datetime, datetime]],
    ) -> list[CalendarActivityEvent]:
        # Group meetings by calendar date (UTC)
        by_date: dict[str, list[tuple[datetime, datetime]]] = {}
        for start, end in meetings:
            date_key = start.astimezone(timezone.utc).strftime("%Y-%m-%d")
            by_date.setdefault(date_key, []).append((start, end))

        events: list[CalendarActivityEvent] = []
        for date_str, day_meetings in sorted(by_date.items()):
            day_meetings.sort(key=lambda m: m[0])
            total_minutes = sum(
                int((end - start).total_seconds() // 60) for start, end in day_meetings
            )
            back_to_back = self._count_back_to_back(day_meetings)
            after_hours_minutes = sum(
                self._after_hours_overlap_minutes(start, end)
                for start, end in day_meetings
            )
            events.append(
                CalendarActivityEvent(
                    workspace_id=self._workspace_id,
                    team_id=team_id,
                    date_utc=date_str,
                    meeting_count=len(day_meetings),
                    total_meeting_minutes=total_minutes,
                    back_to_back_count=back_to_back,
                    after_hours_meeting_minutes=after_hours_minutes,
                )
            )
        return events

    @staticmethod
    def _count_back_to_back(
        sorted_meetings: list[tuple[datetime, datetime]],
    ) -> int:
        count = 0
        for i in range(1, len(sorted_meetings)):
            gap = sorted_meetings[i][0] - sorted_meetings[i - 1][1]
            if timedelta(0) <= gap < timedelta(minutes=_BACK_TO_BACK_GAP_MINUTES):
                count += 1
        return count

    @staticmethod
    def _after_hours_overlap_minutes(start: datetime, end: datetime) -> int:
        """Count minutes of a meeting that fall outside 09:00-18:00 UTC."""
        s = start.astimezone(timezone.utc)
        e = end.astimezone(timezone.utc)
        date = s.date()
        work_start = datetime(date.year, date.month, date.day, _WORK_HOURS_START, tzinfo=timezone.utc)
        work_end = datetime(date.year, date.month, date.day, _WORK_HOURS_END, tzinfo=timezone.utc)

        before = max(timedelta(0), work_start - s)
        after = max(timedelta(0), e - work_end)
        return int((before + after).total_seconds() // 60)
