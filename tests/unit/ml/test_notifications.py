"""Unit tests for ml.inference.notifications — SlackNotifier & SendGridNotifier."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from ml.inference.alert_engine import Alert
from ml.inference.interventions import Intervention
from ml.inference.notifications import (
    SendGridNotifier,
    SlackNotifier,
    _build_sendgrid_payload,
    _build_slack_payload,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_alert(interventions: list[Intervention] | None = None) -> Alert:
    return Alert(
        team_id="T-42",
        workspace_id="W-1",
        trigger_date="2024-01-15",
        consecutive_red_days=3,
        interventions=interventions or [],
        features={
            "calendar_density_score": 0.85,
            "after_hours_activity_index": 0.75,
            "context_switch_count": 0.70,
            "sprint_health_index": 0.25,
        },
    )


def _make_intervention(id_: str = "focus_blocks") -> Intervention:
    return Intervention(
        id=id_,
        title="Focus Blocks",
        description="Schedule 2-hour uninterrupted work blocks.",
    )


_SLACK_URL = "https://hooks.slack.com/services/TEST/HOOK"
_SG_URL = "https://api.sendgrid.com/v3/mail/send"


# ── Payload builders ──────────────────────────────────────────────────────────


def test_slack_payload_contains_team_id() -> None:
    alert = _make_alert()
    payload = _build_slack_payload(alert)
    assert "T-42" in payload["text"]


def test_slack_payload_contains_consecutive_days() -> None:
    alert = _make_alert()
    payload = _build_slack_payload(alert)
    assert "3" in payload["text"]


def test_slack_payload_contains_trigger_date() -> None:
    alert = _make_alert()
    payload = _build_slack_payload(alert)
    assert "2024-01-15" in payload["text"]


def test_slack_payload_contains_intervention_title() -> None:
    alert = _make_alert(interventions=[_make_intervention()])
    payload = _build_slack_payload(alert)
    assert "Focus Blocks" in payload["text"]


def test_slack_payload_no_interventions_has_fallback() -> None:
    alert = _make_alert(interventions=[])
    payload = _build_slack_payload(alert)
    assert "No specific interventions" in payload["text"]


def test_sendgrid_payload_has_correct_to_email() -> None:
    alert = _make_alert()
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    assert payload["personalizations"][0]["to"][0]["email"] == "hr@example.com"


def test_sendgrid_payload_has_correct_from_email() -> None:
    alert = _make_alert()
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    assert payload["from"]["email"] == "from@example.com"


def test_sendgrid_payload_subject_contains_team_id() -> None:
    alert = _make_alert()
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    assert "T-42" in payload["subject"]


def test_sendgrid_payload_subject_contains_consecutive_days() -> None:
    alert = _make_alert()
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    assert "3" in payload["subject"]


def test_sendgrid_payload_content_contains_intervention_title() -> None:
    alert = _make_alert(interventions=[_make_intervention()])
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    html = payload["content"][0]["value"]
    assert "Focus Blocks" in html


def test_sendgrid_payload_no_interventions_has_fallback() -> None:
    alert = _make_alert(interventions=[])
    payload = _build_sendgrid_payload(alert, "from@example.com", "hr@example.com")
    html = payload["content"][0]["value"]
    assert "No specific interventions" in html


# ── SlackNotifier — missing credentials ───────────────────────────────────────


@pytest.mark.asyncio
async def test_slack_missing_url_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    notifier = SlackNotifier(webhook_url=None)
    result = await notifier.send(_make_alert())
    assert result is False


@pytest.mark.asyncio
async def test_slack_missing_url_makes_no_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    notifier = SlackNotifier(webhook_url=None)
    with respx.mock(assert_all_called=False) as mock:
        await notifier.send(_make_alert())
        assert mock.calls.call_count == 0


# ── SlackNotifier — 2xx success ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slack_success_returns_true() -> None:
    with respx.mock() as mock:
        mock.post(_SLACK_URL).mock(return_value=Response(200))
        notifier = SlackNotifier(webhook_url=_SLACK_URL)
        result = await notifier.send(_make_alert())
    assert result is True


@pytest.mark.asyncio
async def test_slack_success_calls_endpoint_once() -> None:
    with respx.mock() as mock:
        route = mock.post(_SLACK_URL).mock(return_value=Response(200))
        notifier = SlackNotifier(webhook_url=_SLACK_URL)
        await notifier.send(_make_alert())
    assert route.called
    assert route.call_count == 1


# ── SlackNotifier — non-2xx responses → retry → failure ──────────────────────


@pytest.mark.asyncio
async def test_slack_non_2xx_retries_three_times() -> None:
    with respx.mock() as mock:
        route = mock.post(_SLACK_URL).mock(return_value=Response(500))
        notifier = SlackNotifier(webhook_url=_SLACK_URL)
        result = await notifier.send(_make_alert())
    assert result is False
    assert route.call_count == 3


@pytest.mark.asyncio
async def test_slack_succeeds_on_second_attempt() -> None:
    responses = [Response(500), Response(200)]
    with respx.mock() as mock:
        mock.post(_SLACK_URL).mock(side_effect=responses)
        notifier = SlackNotifier(webhook_url=_SLACK_URL)
        result = await notifier.send(_make_alert())
    assert result is True


# ── SendGridNotifier — missing credentials ────────────────────────────────────


@pytest.mark.asyncio
async def test_sendgrid_missing_key_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("SENDGRID_FROM_EMAIL", raising=False)
    monkeypatch.delenv("HR_ALERT_EMAIL", raising=False)
    notifier = SendGridNotifier()
    result = await notifier.send(_make_alert())
    assert result is False


@pytest.mark.asyncio
async def test_sendgrid_partial_credentials_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SENDGRID_FROM_EMAIL", raising=False)
    monkeypatch.delenv("HR_ALERT_EMAIL", raising=False)
    notifier = SendGridNotifier(api_key="SG.test", from_email=None, to_email=None)
    result = await notifier.send(_make_alert())
    assert result is False


@pytest.mark.asyncio
async def test_sendgrid_missing_credentials_no_http_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("SENDGRID_FROM_EMAIL", raising=False)
    monkeypatch.delenv("HR_ALERT_EMAIL", raising=False)
    notifier = SendGridNotifier()
    with respx.mock(assert_all_called=False) as mock:
        await notifier.send(_make_alert())
        assert mock.calls.call_count == 0


# ── SendGridNotifier — 2xx success ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_sendgrid_success_returns_true() -> None:
    with respx.mock() as mock:
        mock.post(_SG_URL).mock(return_value=Response(202))
        notifier = SendGridNotifier(
            api_key="SG.test",
            from_email="from@example.com",
            to_email="hr@example.com",
        )
        result = await notifier.send(_make_alert())
    assert result is True


@pytest.mark.asyncio
async def test_sendgrid_sends_auth_header() -> None:
    with respx.mock() as mock:
        route = mock.post(_SG_URL).mock(return_value=Response(202))
        notifier = SendGridNotifier(
            api_key="SG.mykey",
            from_email="from@example.com",
            to_email="hr@example.com",
        )
        await notifier.send(_make_alert())
    request = route.calls[0].request
    assert "Bearer SG.mykey" in request.headers.get("authorization", "")


# ── SendGridNotifier — non-2xx → retry → failure ─────────────────────────────


@pytest.mark.asyncio
async def test_sendgrid_non_2xx_retries_three_times() -> None:
    with respx.mock() as mock:
        route = mock.post(_SG_URL).mock(return_value=Response(400))
        notifier = SendGridNotifier(
            api_key="SG.test",
            from_email="from@example.com",
            to_email="hr@example.com",
        )
        result = await notifier.send(_make_alert())
    assert result is False
    assert route.call_count == 3


@pytest.mark.asyncio
async def test_sendgrid_succeeds_on_third_attempt() -> None:
    responses = [Response(500), Response(500), Response(202)]
    with respx.mock() as mock:
        mock.post(_SG_URL).mock(side_effect=responses)
        notifier = SendGridNotifier(
            api_key="SG.test",
            from_email="from@example.com",
            to_email="hr@example.com",
        )
        result = await notifier.send(_make_alert())
    assert result is True
