"""Jira integration adapter.

Creates a Jira Epic with a pre-filled "Load Redistribution" checklist template
when the intervention is accepted by an HR Admin.

In staging (JIRA_API_TOKEN not set): returns a simulated result.

Environment variables:
  JIRA_BASE_URL    e.g. https://acme.atlassian.net
  JIRA_API_TOKEN   Personal Access Token (PAT) or Basic auth token
  JIRA_USER_EMAIL  Authenticated user email (for Basic auth)
  JIRA_PROJECT_KEY e.g. BURN
"""

from __future__ import annotations

import logging
import os
import uuid

import httpx

from api.schemas.interventions import IntegrationResult

logger = logging.getLogger(__name__)

_CHECKLIST_TEMPLATE = """
*Capacity Review — Load Redistribution Checklist*

h3. Actions
# Review current sprint commitment with the team
# Identify over-allocated team members (>80% capacity)
# Negotiate story point deferral with Product (target: ≥20% reduction)
# Update Jira sprint board to reflect revised scope
# Schedule follow-up in 2 weeks to verify AFS trend

h3. Definition of Done
* Sprint commitment reduced by ≥20%
* Team's AFS tracked for 14 days post-change
* Retrospective note added
""".strip()


async def create_load_redistribution_epic(
    team_id: str,
    team_name: str,
    actor_email: str,
    applied_at: str,
) -> IntegrationResult:
    """Create a Jira Epic with the Load Redistribution checklist template.

    Returns:
        IntegrationResult with the created issue key on success.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    token    = os.getenv("JIRA_API_TOKEN")

    if not base_url or not token:
        logger.warning(
            "[STAGING] Jira credentials not set — simulating Load Redistribution "
            "epic for team %s by %s", team_id, actor_email
        )
        return IntegrationResult(
            integration="jira",
            status="success",
            external_id=f"BURN-{uuid.uuid4().hex[:4].upper()}",
            detail="Staging simulation — no real Jira epic created.",
        )

    project_key = os.getenv("JIRA_PROJECT_KEY", "BURN")
    user_email  = os.getenv("JIRA_USER_EMAIL", actor_email)

    try:
        issue_key = await _create_epic(
            base_url, token, user_email, project_key, team_name, applied_at
        )
        logger.info("Jira epic created: %s for team %s", issue_key, team_id)
        return IntegrationResult(
            integration="jira",
            status="success",
            external_id=issue_key,
            detail=f"Epic {issue_key} created with load redistribution checklist.",
        )
    except Exception as exc:
        logger.error("Jira error for team %s: %s", team_id, exc)
        return IntegrationResult(
            integration="jira",
            status="failed",
            detail=str(exc),
        )


async def _create_epic(
    base_url: str, token: str, user_email: str,
    project_key: str, team_name: str, applied_at: str,
) -> str:
    import base64

    auth = base64.b64encode(f"{user_email}:{token}".encode()).decode()
    payload = {
        "fields": {
            "project":     {"key": project_key},
            "issuetype":   {"name": "Epic"},
            "summary":     f"[Burnout Guardrail] Load Redistribution — {team_name}",
            "description": {
                "type": "doc", "version": 1,
                "content": [
                    {"type": "paragraph", "content": [
                        {"type": "text", "text": (
                            f"Triggered by Burnout Guardrail on {applied_at[:10]}."
                            f"\n\n{_CHECKLIST_TEMPLATE}"
                        )}
                    ]}
                ],
            },
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/rest/api/3/issue",
            json=payload,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return str(resp.json()["key"])
