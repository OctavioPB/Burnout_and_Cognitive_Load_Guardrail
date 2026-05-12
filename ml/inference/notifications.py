"""Async notification adapters for HR alert delivery.

Two adapters are provided:

- **SlackNotifier** — POST to a Slack Incoming Webhook URL.
- **SendGridNotifier** — POST to the SendGrid Mail Send API.

Both are async (httpx) and implement a 3-attempt retry with exponential
back-off.  Credentials are read from environment variables; missing
credentials cause the send to be skipped with a warning rather than a crash,
so a misconfigured notifier does not block the prediction pipeline.

Environment variables
---------------------
SLACK_WEBHOOK_URL       Full webhook URL (set by Slack app configuration)
SENDGRID_API_KEY        SendGrid API key (starts with "SG.")
SENDGRID_FROM_EMAIL     Sender address registered in SendGrid
HR_ALERT_EMAIL          Destination email address for HR alerts
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from ml.inference.alert_engine import Alert

logger = logging.getLogger(__name__)

_MAX_RETRIES: int = 3
_RETRY_BASE_DELAY: float = 0.5  # seconds; doubles on each retry


# ── Payload builders ──────────────────────────────────────────────────────────


def _build_slack_payload(alert: Alert) -> dict[str, Any]:
    intervention_lines = "\n".join(
        f"• *{i.title}*: {i.description}" for i in alert.interventions
    ) or "No specific interventions triggered."

    return {
        "text": (
            f":red_circle: *Burnout Alert — Team `{alert.team_id}`*\n"
            f"*{alert.consecutive_red_days} consecutive Red Zone days* "
            f"(last: {alert.trigger_date})\n\n"
            f"*Suggested interventions:*\n{intervention_lines}"
        )
    }


def _build_sendgrid_payload(alert: Alert, from_email: str, to_email: str) -> dict[str, Any]:
    intervention_html = "".join(
        f"<li><strong>{i.title}</strong>: {i.description}</li>"
        for i in alert.interventions
    ) or "<li>No specific interventions triggered.</li>"

    return {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": (
            f"Burnout Alert: Team {alert.team_id} - {alert.consecutive_red_days} Red Zone Days"
        ),
        "content": [
            {
                "type": "text/html",
                "value": (
                    f"<p>Team <strong>{alert.team_id}</strong> has been in the Red Resilience Zone "
                    f"for <strong>{alert.consecutive_red_days} consecutive days</strong> "
                    f"(last recorded: {alert.trigger_date}).</p>"
                    f"<h3>Suggested Interventions</h3><ul>{intervention_html}</ul>"
                    "<hr><p style='color:#888;font-size:11px;'>"
                    "Burnout &amp; Cognitive Load Guardrail - automated alert. Do not reply.</p>"
                ),
            }
        ],
    }


# ── Retry helper ──────────────────────────────────────────────────────────────


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    json: dict[str, Any],
    headers: dict[str, str] | None = None,
    *,
    description: str = "HTTP POST",
) -> bool:
    """POST *json* to *url* with exponential back-off retry.

    Returns:
        True if a 2xx response was received, False otherwise.
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = await client.post(url, json=json, headers=headers or {}, timeout=10.0)
            if resp.is_success:
                logger.info("%s succeeded (attempt %d)", description, attempt)
                return True
            logger.warning(
                "%s returned %d (attempt %d/%d): %s",
                description,
                resp.status_code,
                attempt,
                _MAX_RETRIES,
                resp.text[:200],
            )
        except httpx.RequestError as exc:
            logger.warning(
                "%s network error (attempt %d/%d): %s", description, attempt, _MAX_RETRIES, exc
            )

        if attempt < _MAX_RETRIES:
            await asyncio.sleep(delay)
            delay *= 2

    logger.error("%s failed after %d attempts", description, _MAX_RETRIES)
    return False


# ── Slack ─────────────────────────────────────────────────────────────────────


@dataclass
class SlackNotifier:
    """Sends alert payloads to a Slack Incoming Webhook.

    Args:
        webhook_url: Override the ``SLACK_WEBHOOK_URL`` env var.
    """

    webhook_url: str | None = None

    async def send(self, alert: Alert) -> bool:
        """Send an alert notification to Slack.

        Args:
            alert: Alert instance produced by AlertEngine.

        Returns:
            True if delivery succeeded, False if skipped or failed.
        """
        url = self.webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not url:
            logger.warning("SLACK_WEBHOOK_URL not set — Slack notification skipped")
            return False

        payload = _build_slack_payload(alert)
        async with httpx.AsyncClient() as client:
            return await _post_with_retry(
                client, url, payload, description=f"Slack alert for team {alert.team_id}"
            )


# ── SendGrid ──────────────────────────────────────────────────────────────────


_SENDGRID_API_URL: str = "https://api.sendgrid.com/v3/mail/send"


@dataclass
class SendGridNotifier:
    """Sends alert emails via the SendGrid Mail Send API.

    Args:
        api_key: Override the ``SENDGRID_API_KEY`` env var.
        from_email: Override the ``SENDGRID_FROM_EMAIL`` env var.
        to_email: Override the ``HR_ALERT_EMAIL`` env var.
    """

    api_key: str | None = None
    from_email: str | None = None
    to_email: str | None = None

    async def send(self, alert: Alert) -> bool:
        """Send an alert notification via SendGrid.

        Args:
            alert: Alert instance produced by AlertEngine.

        Returns:
            True if delivery succeeded, False if skipped or failed.
        """
        key = self.api_key or os.getenv("SENDGRID_API_KEY")
        from_addr = self.from_email or os.getenv("SENDGRID_FROM_EMAIL")
        to_addr = self.to_email or os.getenv("HR_ALERT_EMAIL")

        if not key or not from_addr or not to_addr:
            logger.warning(
                "SendGrid credentials incomplete (SENDGRID_API_KEY / "
                "SENDGRID_FROM_EMAIL / HR_ALERT_EMAIL) — email notification skipped"
            )
            return False

        payload = _build_sendgrid_payload(alert, from_addr, to_addr)
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            return await _post_with_retry(
                client,
                _SENDGRID_API_URL,
                payload,
                headers=headers,
                description=f"SendGrid alert for team {alert.team_id}",
            )
