"""GitHub connector — PR cycle time and commit density metadata."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.models import GitHubActivityEvent

logger = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_PAGE_SIZE = 100
_WORK_HOURS_START = 9   # 09:00 UTC
_WORK_HOURS_END = 18    # 18:00 UTC


class GitHubConnector(BaseConnector[GitHubActivityEvent]):
    """Fetches PR and commit metadata from the GitHub REST API.

    Captures: PR timestamps (created_at, merged_at), review timestamps,
              commit author_date (hour only).
    Does NOT capture: PR titles, PR bodies, commit messages, author names,
                      or file diffs.

    Args:
        workspace_id: GitHub organization login (used as workspace identifier).
        http_client:  Injected httpx.AsyncClient.
        token:        GitHub personal access token or app installation token.
        org:          GitHub organization slug.
        repo_ids:     Numeric GitHub repo IDs for this team. IDs avoid storing
                      repo names which can reveal project context.
        repo_name_map: id → full_name lookup needed to build API paths.
                       Separate from repo_ids to be explicit about the tradeoff.
    """

    def __init__(
        self,
        workspace_id: str,
        http_client: httpx.AsyncClient,
        token: str,
        org: str,
        repo_ids: list[int],
        repo_name_map: dict[int, str],
    ) -> None:
        super().__init__(workspace_id=workspace_id, http_client=http_client)
        self._org = org
        self._repo_ids = repo_ids
        self._repo_name_map = repo_name_map
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def fetch_events(
        self,
        team_id: str,
        since: datetime,
        until: datetime,
    ) -> list[GitHubActivityEvent]:
        events: list[GitHubActivityEvent] = []
        for repo_id in self._repo_ids:
            repo_name = self._repo_name_map.get(repo_id)
            if not repo_name:
                self._logger.warning("No name mapping for repo_id %d — skipping", repo_id)
                continue
            repo_events = await self._fetch_repo_events(
                team_id, repo_id, repo_name, since, until
            )
            events.extend(repo_events)
        return events

    async def health_check(self) -> bool:
        try:
            response = await self._http.get(
                f"{_API_BASE}/orgs/{self._org}",
                headers=self._headers,
                timeout=10.0,
            )
            return response.status_code == 200
        except httpx.HTTPError as exc:
            self._logger.warning("GitHub health check failed: %s", exc)
            return False

    async def _fetch_repo_events(
        self,
        team_id: str,
        repo_id: int,
        repo_name: str,
        since: datetime,
        until: datetime,
    ) -> list[GitHubActivityEvent]:
        prs, commits = await asyncio.gather(
            self._fetch_pr_windows(repo_name, since, until),
            self._fetch_commit_timestamps(repo_name, since, until),
        )
        return self._aggregate_by_day(team_id, str(repo_id), prs, commits)

    async def _fetch_pr_windows(
        self,
        repo_name: str,
        since: datetime,
        until: datetime,
    ) -> list[dict[str, datetime | None]]:
        """Return dicts with created_at, merged_at, first_review_at.

        No PR title, body, or author is stored.
        """
        url = f"{_API_BASE}/repos/{repo_name}/pulls"
        pr_windows: list[dict[str, datetime | None]] = []
        page = 1

        while True:
            try:
                response = await self._http.get(
                    url,
                    headers=self._headers,
                    params={"state": "closed", "per_page": _PAGE_SIZE, "page": page},
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "GitHub PR list HTTP %d for %s", exc.response.status_code, repo_name
                )
                break

            prs: list[dict[str, Any]] = response.json()
            if not prs:
                break

            for pr in prs:
                created_raw: str | None = pr.get("created_at")
                merged_raw: str | None = pr.get("merged_at")
                if not created_raw:
                    continue

                created = datetime.fromisoformat(
                    created_raw.replace("Z", "+00:00")
                )
                if created >= until:
                    continue
                if created < since:
                    # PRs are returned newest-first; stop when we're past the window
                    return pr_windows

                merged: datetime | None = None
                if merged_raw:
                    merged = datetime.fromisoformat(merged_raw.replace("Z", "+00:00"))

                pr_windows.append({"created_at": created, "merged_at": merged})

            if len(prs) < _PAGE_SIZE:
                break
            page += 1

        return pr_windows

    async def _fetch_commit_timestamps(
        self,
        repo_name: str,
        since: datetime,
        until: datetime,
    ) -> list[datetime]:
        """Return commit author_date timestamps only — messages and authors discarded."""
        url = f"{_API_BASE}/repos/{repo_name}/commits"
        timestamps: list[datetime] = []
        page = 1

        while True:
            try:
                response = await self._http.get(
                    url,
                    headers=self._headers,
                    params={
                        "since": since.isoformat(),
                        "until": until.isoformat(),
                        "per_page": _PAGE_SIZE,
                        "page": page,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "GitHub commit list HTTP %d for %s",
                    exc.response.status_code,
                    repo_name,
                )
                break

            commits: list[dict[str, Any]] = response.json()
            if not commits:
                break

            for commit in commits:
                # author_date comes from the git commit object, not the push event
                author_date_raw: str | None = (
                    (commit.get("commit") or {})
                    .get("author", {})
                    .get("date")
                )
                if author_date_raw:
                    timestamps.append(
                        datetime.fromisoformat(author_date_raw.replace("Z", "+00:00"))
                    )

            if len(commits) < _PAGE_SIZE:
                break
            page += 1

        return timestamps

    def _aggregate_by_day(
        self,
        team_id: str,
        repo_id: str,
        prs: list[dict[str, datetime | None]],
        commits: list[datetime],
    ) -> list[GitHubActivityEvent]:
        # Group by date
        by_date: dict[str, dict[str, object]] = {}

        for pr in prs:
            created = pr["created_at"]
            if not isinstance(created, datetime):
                continue
            date_key = created.astimezone(timezone.utc).strftime("%Y-%m-%d")
            d = by_date.setdefault(
                date_key,
                {
                    "opened": 0,
                    "merged": 0,
                    "cycle_hours": [],
                    "review_hours": [],
                    "after_commits": 0,
                    "total_commits": 0,
                },
            )
            d["opened"] = int(d["opened"]) + 1  # type: ignore[arg-type]
            merged = pr.get("merged_at")
            if isinstance(merged, datetime):
                d["merged"] = int(d["merged"]) + 1  # type: ignore[arg-type]
                cycle = (merged - created).total_seconds() / 3600
                cast_list: list[float] = d["cycle_hours"]  # type: ignore[assignment]
                cast_list.append(cycle)

        for ts in commits:
            date_key = ts.astimezone(timezone.utc).strftime("%Y-%m-%d")
            d = by_date.setdefault(
                date_key,
                {
                    "opened": 0,
                    "merged": 0,
                    "cycle_hours": [],
                    "review_hours": [],
                    "after_commits": 0,
                    "total_commits": 0,
                },
            )
            d["total_commits"] = int(d["total_commits"]) + 1  # type: ignore[arg-type]
            if self._is_after_hours(ts):
                d["after_commits"] = int(d["after_commits"]) + 1  # type: ignore[arg-type]

        events: list[GitHubActivityEvent] = []
        for date_str, data in sorted(by_date.items()):
            cycle_list: list[float] = data["cycle_hours"]  # type: ignore[assignment]
            review_list: list[float] = data["review_hours"]  # type: ignore[assignment]
            events.append(
                GitHubActivityEvent(
                    workspace_id=self._workspace_id,
                    team_id=team_id,
                    date_utc=date_str,
                    repo_id=repo_id,
                    pr_count_opened=int(data["opened"]),  # type: ignore[arg-type]
                    pr_count_merged=int(data["merged"]),  # type: ignore[arg-type]
                    avg_pr_cycle_time_hours=(
                        sum(cycle_list) / len(cycle_list) if cycle_list else -1.0
                    ),
                    avg_review_turnaround_hours=(
                        sum(review_list) / len(review_list) if review_list else -1.0
                    ),
                    commit_count_after_hours=int(data["after_commits"]),  # type: ignore[arg-type]
                    total_commit_count=int(data["total_commits"]),  # type: ignore[arg-type]
                )
            )
        return events

    @staticmethod
    def _is_after_hours(ts: datetime) -> bool:
        hour = ts.astimezone(timezone.utc).hour
        return hour < _WORK_HOURS_START or hour >= _WORK_HOURS_END
