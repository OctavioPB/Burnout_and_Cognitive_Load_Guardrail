"""Slack integration adapter.

Posts a pinned message to the team's Slack channel when HR accepts the
"Async-First Week" intervention.  The message *content* is written by the HR
manager — the system only delivers it (privacy rule: no system-generated content).

In staging (SLACK_WEBHOOK_URL not set): returns a simulated result.

Environment variables:
  SLACK_BOT_TOKEN      xoxb-... token with chat:write and pins:write scopes
  SLACK_CHANNEL_{ID}   Channel ID for a given team_id (e.g. SLACK_CHANNEL_T-01=C12345)
  SLACK_FALLBACK_CHANNEL  Default channel if team-specific mapping is missing
"""

from __future__ import annotations

import logging
import os
import uuid

import httpx

from api.schemas.interventions import IntegrationResult

logger = logging.getLogger(__name__)

_SLACK_POST_URL = "https://slack.com/api/chat.postMessage"
_SLACK_PIN_URL  = "https://slack.com/api/pins.add"


def _channel_for_team(team_id: str) -> str | None:
    """Look up the Slack channel ID for a team from env vars."""
    env_key = f"SLACK_CHANNEL_{team_id.replace('-', '_')}"
    return os.getenv(env_key) or os.getenv("SLACK_FALLBACK_CHANNEL")


async def post_async_first_week_notice(
    team_id: str,
    team_name: str,
    hr_message: str,
    actor_name: str,
) -> IntegrationResult:
    """Post and pin an HR-authored async-first week notice to the team channel.

    Args:
        team_id:    Team identifier (used to resolve channel mapping).
        team_name:  Human-readable team name.
        hr_message: Message text written by the HR manager.
        actor_name: Name of the HR actor (shown in the footer).

    Returns:
        IntegrationResult with the Slack message timestamp on success.
    """
    token = os.getenv("SLACK_BOT_TOKEN")

    if not token:
        logger.warning(
            "[STAGING] Slack bot token not set — simulating async-first week "
            "notice for team %s", team_id
        )
        return IntegrationResult(
            integration="slack",
            status="success",
            external_id=f"staging-ts-{uuid.uuid4().hex[:8]}",
            detail="Staging simulation — no real Slack message posted.",
        )

    channel = _channel_for_team(team_id)
    if not channel:
        return IntegrationResult(
            integration="slack",
            status="failed",
            detail=f"No Slack channel configured for team {team_id}. "
                   "Set SLACK_CHANNEL_{team_id} or SLACK_FALLBACK_CHANNEL.",
        )

    try:
        ts = await _post_and_pin(token, channel, team_name, hr_message, actor_name)
        logger.info("Slack message posted and pinned for team %s (ts=%s)", team_id, ts)
        return IntegrationResult(
            integration="slack",
            status="success",
            external_id=ts,
            detail=f"Message posted and pinned in channel {channel}.",
        )
    except Exception as exc:
        logger.error("Slack error for team %s: %s", team_id, exc)
        return IntegrationResult(
            integration="slack",
            status="failed",
            detail=str(exc),
        )


async def _post_and_pin(
    token: str, channel: str, team_name: str, hr_message: str, actor_name: str,
) -> str:
    """POST the message then pin it; return the message timestamp."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "channel": channel,
        "text": hr_message,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Async-First Week - {team_name}*\n\n{hr_message}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Posted by {actor_name} via Burnout Guardrail"}
                ],
            },
        ],
    }

    async with httpx.AsyncClient() as client:
        post_resp = await client.post(_SLACK_POST_URL, json=payload, headers=headers)
        post_resp.raise_for_status()
        data = post_resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
        ts: str = data["ts"]

        # Pin the message
        await client.post(
            _SLACK_PIN_URL,
            json={"channel": channel, "timestamp": ts},
            headers=headers,
        )

    return ts
