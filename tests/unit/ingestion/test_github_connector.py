"""Unit tests for GitHubConnector."""

from __future__ import annotations

import httpx
import pytest
import respx

from ingestion.connectors.github import GitHubConnector
from ingestion.models import GitHubActivityEvent
from tests.unit.ingestion.conftest import SINCE, TEAM_ID, UNTIL, WORKSPACE_ID

_API_BASE = "https://api.github.com"
_ORG = "acme-org"
_REPO_ID = 123456
_REPO_NAME = "acme-org/backend"


def _make_connector(client: httpx.AsyncClient) -> GitHubConnector:
    return GitHubConnector(
        workspace_id=WORKSPACE_ID,
        http_client=client,
        token="ghp_test_token",
        org=_ORG,
        repo_ids=[_REPO_ID],
        repo_name_map={_REPO_ID: _REPO_NAME},
    )


def _pr(created: str, merged: str | None = None) -> dict:
    return {
        "number": 1,
        "created_at": created,
        "merged_at": merged,
        # title and body deliberately omitted — connector must not read them
    }


def _commit(date: str) -> dict:
    return {
        "sha": "abc123",
        "commit": {
            "author": {"date": date},
            # message deliberately omitted
        },
    }


# ── fetch_events ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_returns_typed_events(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(
            200,
            json=[
                _pr("2024-01-15T10:00:00Z", "2024-01-15T14:00:00Z"),
            ],
        )
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(
            200,
            json=[_commit("2024-01-15T10:30:00Z"), _commit("2024-01-15T22:00:00Z")],
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert len(events) == 1
    assert isinstance(events[0], GitHubActivityEvent)
    assert events[0].repo_id == str(_REPO_ID)
    assert events[0].date_utc == "2024-01-15"


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_computes_pr_cycle_time(
    async_http_client: httpx.AsyncClient,
) -> None:
    # PR open: 10:00 → merged: 14:00 = 4 hours cycle time
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(
            200,
            json=[_pr("2024-01-15T10:00:00Z", "2024-01-15T14:00:00Z")],
        )
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(200, json=[])
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert abs(events[0].avg_pr_cycle_time_hours - 4.0) < 0.01


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_counts_after_hours_commits(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(
            200,
            json=[
                _commit("2024-01-15T10:00:00Z"),  # work hours
                _commit("2024-01-15T22:00:00Z"),  # after hours
                _commit("2024-01-15T06:00:00Z"),  # before hours
            ],
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert events[0].total_commit_count == 3
    assert events[0].commit_count_after_hours == 2


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_uses_repo_id_not_name(
    async_http_client: httpx.AsyncClient,
) -> None:
    """repo_id must be a numeric string, never the org/repo name."""
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(200, json=[_pr("2024-01-15T12:00:00Z")])
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(200, json=[])
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert events[0].repo_id == str(_REPO_ID)
    assert _REPO_NAME not in events[0].model_dump_json()
    assert _ORG not in events[0].model_dump_json()


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_no_commit_messages_in_output(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "sha": "abc",
                    "commit": {
                        "author": {"date": "2024-01-15T10:00:00Z"},
                        "message": "SECRET COMMIT MSG",
                    },
                }
            ],
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert "SECRET" not in events[0].model_dump_json()


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_events_returns_empty_on_http_error(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/pulls").mock(
        return_value=httpx.Response(401)
    )
    respx.get(f"{_API_BASE}/repos/{_REPO_NAME}/commits").mock(
        return_value=httpx.Response(401)
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)
    assert events == []
