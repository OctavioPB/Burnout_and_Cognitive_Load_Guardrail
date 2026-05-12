"""Unit tests for SlackConnector."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from ingestion.connectors.slack import SlackConnector
from ingestion.models import SlackActivityEvent
from tests.unit.ingestion.conftest import SINCE, TEAM_ID, UNTIL, WORKSPACE_ID

_BOT_TOKEN = "xoxb-test-token"
_CHANNEL_IDS = ["C001", "C002"]


def _make_connector(client: httpx.AsyncClient) -> SlackConnector:
    return SlackConnector(
        workspace_id=WORKSPACE_ID,
        http_client=client,
        bot_token=_BOT_TOKEN,
        channel_ids=_CHANNEL_IDS,
    )


# ── fetch_events ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_slack_fetch_events_returns_typed_events(
    async_http_client: httpx.AsyncClient,
) -> None:
    # 2 messages in channel C001: one at 14:00, one at 14:30 (same bucket)
    # 1 message in channel C002: at 22:00 (after hours)
    ts_14h = str(datetime(2024, 1, 15, 14, 0, tzinfo=UTC).timestamp())
    ts_14h30 = str(datetime(2024, 1, 15, 14, 30, tzinfo=UTC).timestamp())
    ts_22h = str(datetime(2024, 1, 15, 22, 5, tzinfo=UTC).timestamp())

    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C001"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [{"ts": ts_14h}, {"ts": ts_14h30}],
                "has_more": False,
                "response_metadata": {"next_cursor": ""},
            },
        )
    )
    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C002"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [{"ts": ts_22h}],
                "has_more": False,
                "response_metadata": {"next_cursor": ""},
            },
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    assert len(events) == 2  # C001@14h + C002@22h
    assert all(isinstance(e, SlackActivityEvent) for e in events)
    assert all(e.workspace_id == WORKSPACE_ID for e in events)
    assert all(e.team_id == TEAM_ID for e in events)


@pytest.mark.asyncio
@respx.mock
async def test_slack_fetch_events_aggregates_messages_into_hour_buckets(
    async_http_client: httpx.AsyncClient,
) -> None:
    ts_14h = str(datetime(2024, 1, 15, 14, 5, tzinfo=UTC).timestamp())
    ts_14h45 = str(datetime(2024, 1, 15, 14, 45, tzinfo=UTC).timestamp())

    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C001"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [{"ts": ts_14h}, {"ts": ts_14h45}],
                "has_more": False,
                "response_metadata": {},
            },
        )
    )
    # C002 returns empty
    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C002"}).mock(
        return_value=httpx.Response(200, json={"ok": True, "messages": [], "response_metadata": {}})
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    c001_events = [e for e in events if e.channel_id == "C001"]
    assert len(c001_events) == 1
    assert c001_events[0].message_count == 2
    assert c001_events[0].hour_bucket_utc.hour == 14


@pytest.mark.asyncio
@respx.mock
async def test_slack_fetch_events_flags_after_hours_correctly(
    async_http_client: httpx.AsyncClient,
) -> None:
    ts_work = str(datetime(2024, 1, 15, 10, 0, tzinfo=UTC).timestamp())
    ts_after = str(datetime(2024, 1, 15, 21, 0, tzinfo=UTC).timestamp())

    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C001"}).mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "messages": [{"ts": ts_work}, {"ts": ts_after}], "response_metadata": {}},
        )
    )
    respx.get("https://slack.com/api/conversations.history", params__contains={"channel": "C002"}).mock(
        return_value=httpx.Response(200, json={"ok": True, "messages": [], "response_metadata": {}})
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    work_event = next(e for e in events if e.hour_bucket_utc.hour == 10)
    after_event = next(e for e in events if e.hour_bucket_utc.hour == 21)
    assert not work_event.is_after_hours
    assert after_event.is_after_hours


@pytest.mark.asyncio
@respx.mock
async def test_slack_fetch_events_contains_no_message_content(
    async_http_client: httpx.AsyncClient,
) -> None:
    ts = str(datetime(2024, 1, 15, 12, 0, tzinfo=UTC).timestamp())
    respx.get("https://slack.com/api/conversations.history").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [{"ts": ts, "text": "SECRET CONTENT", "user": "U123"}],
                "response_metadata": {},
            },
        )
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)

    for event in events:
        assert not hasattr(event, "text")
        assert not hasattr(event, "user_id")
        assert not hasattr(event, "user")
        assert "SECRET" not in event.model_dump_json()


@pytest.mark.asyncio
@respx.mock
async def test_slack_fetch_events_returns_empty_on_api_error(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get("https://slack.com/api/conversations.history").mock(
        return_value=httpx.Response(401, json={"ok": False, "error": "invalid_auth"})
    )

    connector = _make_connector(async_http_client)
    events = await connector.fetch_events(TEAM_ID, SINCE, UNTIL)
    assert events == []


# ── health_check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_slack_health_check_returns_true_when_api_ok(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get("https://slack.com/api/auth.test").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    connector = _make_connector(async_http_client)
    assert await connector.health_check() is True


@pytest.mark.asyncio
@respx.mock
async def test_slack_health_check_returns_false_when_api_fails(
    async_http_client: httpx.AsyncClient,
) -> None:
    respx.get("https://slack.com/api/auth.test").mock(
        return_value=httpx.Response(200, json={"ok": False, "error": "not_authed"})
    )
    connector = _make_connector(async_http_client)
    assert await connector.health_check() is False
