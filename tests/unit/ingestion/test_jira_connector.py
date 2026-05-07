"""Unit tests for JiraConnector."""

from __future__ import annotations

import httpx
import pytest
import respx

from ingestion.connectors.jira import JiraConnector
from ingestion.models import JiraSprintEvent
from tests.unit.ingestion.conftest import SINCE, TEAM_ID, UNTIL, WORKSPACE_ID

_BASE_URL = "https://acme.atlassian.net"
_BOARD_ID = 42


def _make_connector(client: httpx.AsyncClient) -> JiraConnector:
    return JiraConnector(
        workspace_id=WORKSPACE_ID,
        http_client=client,
        base_url=_BASE_URL,
        email="test@acme.com",
        api_token="fake_token",
        board_id=_BOARD_ID,
    )


def _sprint_response(sprints: list[dict]) -> dict:
    return {"values": sprints, "isLast": True}


def _sprint(sprint_id: int = 1) -> dict:
    return {
        "id": sprint_id,
        "state": "closed",
        "startDate": "2024-01-08T09:00:00.000Z",
        "endDate": "2024-01-15T18:00:00.000Z",
        "completeDate": "2024-01-15T18:00:00.000Z",
    }


def _issue_response(issues: list[dict]) -> dict:
    return {"issues": issues, "total": len(issues)}


def _issue(points: int, status: str = "In Progress") -> dict:
    return {
        "fields": {
            "customfield_10016": points,
            "status": {"name": status},
        }
    }


# ── fetch_events ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_jira_fetch_events_returns_typed_events(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint").mock(
        return_value=httpx.Response(200, json=_sprint_response([_sprint(1)]))
    )
    respx.get(f"{_BASE_URL}/rest/agile/1.0/sprint/1/issue").mock(
        return_value=httpx.Response(
            200,
            json=_issue_response([_issue(3, "Done"), _issue(5, "In Progress")]),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert len(events) == 1
    assert isinstance(events[0], JiraSprintEvent)
    assert events[0].committed_points == 8
    assert events[0].completed_points == 3


@pytest.mark.asyncio
@respx.mock
async def test_jira_fetch_events_computes_delivery_ratio(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint").mock(
        return_value=httpx.Response(200, json=_sprint_response([_sprint(1)]))
    )
    respx.get(f"{_BASE_URL}/rest/agile/1.0/sprint/1/issue").mock(
        return_value=httpx.Response(
            200,
            json=_issue_response([
                _issue(10, "Done"),
                _issue(10, "Done"),
                _issue(10, "In Progress"),
                _issue(10, "In Progress"),
            ]),
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert abs(events[0].delivery_ratio - 0.5) < 0.001


@pytest.mark.asyncio
@respx.mock
async def test_jira_fetch_events_delivery_ratio_zero_when_no_committed(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint").mock(
        return_value=httpx.Response(200, json=_sprint_response([_sprint(1)]))
    )
    # All issues have 0 story points
    respx.get(f"{_BASE_URL}/rest/agile/1.0/sprint/1/issue").mock(
        return_value=httpx.Response(
            200, json=_issue_response([_issue(0, "Done"), _issue(0, "In Progress")])
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert events[0].delivery_ratio == 0.0


@pytest.mark.asyncio
@respx.mock
async def test_jira_fetch_events_contains_no_issue_titles(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint").mock(
        return_value=httpx.Response(200, json=_sprint_response([_sprint(1)]))
    )
    respx.get(f"{_BASE_URL}/rest/agile/1.0/sprint/1/issue").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "fields": {
                            "summary": "SECRET TASK NAME",
                            "customfield_10016": 5,
                            "status": {"name": "Done"},
                        }
                    }
                ],
                "total": 1,
            },
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert "SECRET" not in events[0].model_dump_json()


@pytest.mark.asyncio
@respx.mock
async def test_jira_fetch_events_returns_empty_on_auth_error(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get(f"{_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint").mock(
        return_value=httpx.Response(401)
    )
    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)
    assert events == []
