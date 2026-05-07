"""Slack connector — channel-level message activity metadata."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.models import SlackActivityEvent

logger = logging.getLogger(__name__)

_API_BASE = "https://slack.com/api"
_WORK_HOURS_START = 9   # 09:00 UTC
_WORK_HOURS_END = 18    # 18:00 UTC
_PAGE_LIMIT = 200


class SlackConnector(BaseConnector[SlackActivityEvent]):
    """Fetches channel message-count metadata from the Slack Web API.

    Captures: message timestamps and per-channel hourly counts.
    Does NOT capture: message text, user IDs, reactions, or thread content.

    Args:
        workspace_id: Slack workspace ID (e.g. W012AB3CD).
        http_client:  Injected httpx.AsyncClient for testability.
        bot_token:    Slack Bot Token (xoxb-…). Kept as a plain string
                      because it is passed in from SecretStr.get_secret_value().
        channel_ids:  Channels to monitor for this team. Should be pre-filtered
                      to public channels the bot is invited to.
    """

    def __init__(
        self,
        workspace_id: str,
        http_client: httpx.AsyncClient,
        bot_token: str,
        channel_ids: list[str],
    ) -> None:
        super().__init__(workspace_id=workspace_id, http_client=http_client)
        self._channel_ids = channel_ids
        self._headers = {"Authorization": f"Bearer {bot_token}"}

    async def fetch_events(
        self,
        team_id: str,
        since: datetime,
        until: datetime,
    ) -> list[SlackActivityEvent]:
        # Aggregate: (channel_id, hour_bucket) → count + flags
        buckets: dict[tuple[str, datetime], dict[str, int | bool]] = {}

        for channel_id in self._channel_ids:
            timestamps = await self._fetch_message_timestamps(channel_id, since, until)
            for ts in timestamps:
                hour = ts.replace(minute=0, second=0, microsecond=0)
                key = (channel_id, hour)
                if key not in buckets:
                    buckets[key] = {
                        "count": 0,
                        "is_after_hours": self._is_after_hours(ts),
                        "day_of_week": hour.weekday(),
                    }
                buckets[key]["count"] = int(buckets[key]["count"]) + 1

        return [
            SlackActivityEvent(
                workspace_id=self._workspace_id,
                team_id=team_id,
                channel_id=channel_id,
                hour_bucket_utc=hour,
                message_count=int(data["count"]),
                is_after_hours=bool(data["is_after_hours"]),
                day_of_week=int(data["day_of_week"]),
            )
            for (channel_id, hour), data in buckets.items()
        ]

    async def health_check(self) -> bool:
        try:
            response = await self._http.get(
                f"{_API_BASE}/auth.test",
                headers=self._headers,
                timeout=10.0,
            )
            result: dict[str, Any] = response.json()
            return bool(result.get("ok", False))
        except httpx.HTTPError as exc:
            self._logger.warning("Slack health check failed: %s", exc)
            return False

    async def _fetch_message_timestamps(
        self,
        channel_id: str,
        since: datetime,
        until: datetime,
    ) -> list[datetime]:
        """Retrieve message timestamps only — message body is discarded immediately."""
        timestamps: list[datetime] = []
        cursor: str | None = None

        while True:
            params: dict[str, str | float | int] = {
                "channel": channel_id,
                "oldest": since.timestamp(),
                "latest": until.timestamp(),
                "limit": _PAGE_LIMIT,
            }
            if cursor:
                params["cursor"] = cursor

            try:
                response = await self._http.get(
                    f"{_API_BASE}/conversations.history",
                    headers=self._headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "Slack API HTTP %d for channel %s",
                    exc.response.status_code,
                    channel_id,
                )
                break

            data: dict[str, Any] = response.json()
            if not data.get("ok"):
                self._logger.warning(
                    "Slack API ok=false for channel %s: %s",
                    channel_id,
                    data.get("error"),
                )
                break

            # Extract timestamp float only — content fields are never read
            for msg in data.get("messages", []):
                ts_str = msg.get("ts", "")
                if ts_str:
                    timestamps.append(
                        datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
                    )

            cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
            if not cursor:
                break

        return timestamps

    @staticmethod
    def _is_after_hours(ts: datetime) -> bool:
        hour = ts.astimezone(timezone.utc).hour
        return hour < _WORK_HOURS_START or hour >= _WORK_HOURS_END
