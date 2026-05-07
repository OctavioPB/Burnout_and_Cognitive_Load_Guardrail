"""Jira connector — sprint commitment vs. delivery metadata."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.models import JiraSprintEvent

logger = logging.getLogger(__name__)

_PAGE_SIZE = 50
_DONE_STATUSES = frozenset({"Done", "Closed", "Resolved"})


class JiraConnector(BaseConnector[JiraSprintEvent]):
    """Fetches sprint commitment and delivery ratios from the Jira Agile REST API.

    Captures: story point counts and sprint dates.
    Does NOT capture: issue titles, descriptions, assignee names, or comments.

    Args:
        workspace_id: Atlassian cloud ID (from Jira cloud account settings).
        http_client:  Injected httpx.AsyncClient.
        base_url:     Jira instance base URL (e.g. https://acme.atlassian.net).
        email:        Atlassian account email for basic auth.
        api_token:    Atlassian API token. Plain string — caller extracts from SecretStr.
        board_id:     Jira board ID for this team.
    """

    def __init__(
        self,
        workspace_id: str,
        http_client: httpx.AsyncClient,
        base_url: str,
        email: str,
        api_token: str,
        board_id: int,
    ) -> None:
        super().__init__(workspace_id=workspace_id, http_client=http_client)
        self._base_url = base_url.rstrip("/")
        self._auth = (email, api_token)
        self._board_id = board_id

    async def fetch_events(
        self,
        team_id: str,
        since: datetime,
        until: datetime,
    ) -> list[JiraSprintEvent]:
        sprints = await self._fetch_sprints(since, until)
        events: list[JiraSprintEvent] = []
        for sprint in sprints:
            event = await self._build_sprint_event(team_id, sprint)
            if event:
                events.append(event)
        return events

    async def health_check(self) -> bool:
        try:
            url = f"{self._base_url}/rest/agile/1.0/board/{self._board_id}"
            response = await self._http.get(url, auth=self._auth, timeout=10.0)
            return response.status_code == 200
        except httpx.HTTPError as exc:
            self._logger.warning("Jira health check failed: %s", exc)
            return False

    async def _fetch_sprints(
        self,
        since: datetime,
        until: datetime,
    ) -> list[dict[str, Any]]:
        """Return sprints that overlap the [since, until) window."""
        url = f"{self._base_url}/rest/agile/1.0/board/{self._board_id}/sprint"
        sprints: list[dict[str, Any]] = []
        start_at = 0

        while True:
            try:
                response = await self._http.get(
                    url,
                    auth=self._auth,
                    params={
                        "state": "active,closed",
                        "startAt": start_at,
                        "maxResults": _PAGE_SIZE,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "Jira sprint list HTTP %d for board %d",
                    exc.response.status_code,
                    self._board_id,
                )
                break

            data: dict[str, Any] = response.json()
            for sprint in data.get("values", []):
                end_date_str: str = sprint.get("endDate", "")
                start_date_str: str = sprint.get("startDate", "")
                if not (start_date_str and end_date_str):
                    continue
                sprint_end = datetime.fromisoformat(
                    end_date_str.replace("Z", "+00:00")
                )
                sprint_start = datetime.fromisoformat(
                    start_date_str.replace("Z", "+00:00")
                )
                # Include sprints that overlap the fetch window
                if sprint_end >= since and sprint_start < until:
                    sprints.append(sprint)

            if data.get("isLast", True):
                break
            start_at += _PAGE_SIZE

        return sprints

    async def _build_sprint_event(
        self,
        team_id: str,
        sprint: dict[str, Any],
    ) -> JiraSprintEvent | None:
        sprint_id = str(sprint.get("id", ""))
        start_date = sprint.get("startDate", "")
        end_date = sprint.get("completeDate") or sprint.get("endDate", "")

        committed, completed = await self._fetch_sprint_points(sprint_id)
        delivery_ratio = (
            round(completed / committed, 4) if committed > 0 else 0.0
        )

        try:
            start_str = datetime.fromisoformat(
                start_date.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
            end_str = datetime.fromisoformat(
                end_date.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            self._logger.warning("Invalid sprint dates for sprint %s", sprint_id)
            return None

        return JiraSprintEvent(
            workspace_id=self._workspace_id,
            team_id=team_id,
            sprint_id=sprint_id,
            board_id=str(self._board_id),
            committed_points=committed,
            completed_points=completed,
            delivery_ratio=delivery_ratio,
            sprint_start_date=start_str,
            sprint_end_date=end_str,
        )

    async def _fetch_sprint_points(
        self,
        sprint_id: str,
    ) -> tuple[int, int]:
        """Return (committed_points, completed_points) for a sprint.

        Issue titles and descriptions are discarded — only story point fields are read.
        """
        url = (
            f"{self._base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        )
        committed = 0
        completed = 0
        start_at = 0

        while True:
            try:
                response = await self._http.get(
                    url,
                    auth=self._auth,
                    params={
                        "startAt": start_at,
                        "maxResults": _PAGE_SIZE,
                        "fields": "story_points,customfield_10016,status",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "Jira issue list HTTP %d for sprint %s",
                    exc.response.status_code,
                    sprint_id,
                )
                break

            data: dict[str, Any] = response.json()
            for issue in data.get("issues", []):
                fields: dict[str, Any] = issue.get("fields", {})
                # story_points stored in customfield_10016 in most Jira Cloud instances
                points_raw = fields.get("story_points") or fields.get("customfield_10016") or 0
                points = int(points_raw) if isinstance(points_raw, (int, float)) else 0
                committed += points

                status_name: str = (
                    (fields.get("status") or {}).get("name") or ""
                )
                if status_name in _DONE_STATUSES:
                    completed += points

            total = data.get("total", 0)
            start_at += _PAGE_SIZE
            if start_at >= total:
                break

        return committed, completed
