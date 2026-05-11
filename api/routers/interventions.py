"""Intervention action endpoints.

POST /interventions/{team_id}/apply    — accept and execute an integration
POST /interventions/{team_id}/dismiss  — dismiss without executing
GET  /interventions/{team_id}          — list all records for a team
GET  /interventions/{team_id}/efficacy/{intervention_id} — before/after AFS view
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from api.schemas.interventions import (
    ApplyInterventionRequest,
    DismissInterventionRequest,
    EfficacyPoint,
    EfficacyView,
    InterventionRecord,
)
from api.services.integrations.calendar_adapter import create_meeting_free_friday
from api.services.integrations.jira_adapter import create_load_redistribution_epic
from api.services.integrations.slack_adapter import post_async_first_week_notice
from api.services.intervention_store import audit_store, intervention_store
from api.services.mock_data import store as data_store
from api.dependencies import require_authenticated, require_team_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interventions", tags=["interventions"])

# ── Integration dispatcher ────────────────────────────────────────────────────

_INTEGRATIONS: dict[str, str] = {
    "meeting_free_friday": "google_calendar",
    "async_first_week":    "slack",
    "load_redistribution": "jira",
    "focus_blocks":        "none",  # internal recommendation — no external integration
}


async def _dispatch(
    intervention_id: str,
    team_id: str,
    team_name: str,
    actor_email: str,
    actor_name: str,
    customization: str | None,
    applied_at: str,
):
    from api.schemas.interventions import IntegrationResult

    match intervention_id:
        case "meeting_free_friday":
            return await create_meeting_free_friday(team_id, team_name, actor_email)
        case "load_redistribution":
            return await create_load_redistribution_epic(team_id, team_name, actor_email, applied_at)
        case "async_first_week":
            message = customization or f"Starting this week, {team_name} will follow an async-first communication protocol."
            return await post_async_first_week_notice(team_id, team_name, message, actor_name)
        case _:
            return IntegrationResult(integration="none", status="skipped", detail="No external integration for this intervention.")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{team_id}/apply", response_model=InterventionRecord)
async def apply_intervention(
    team_id: str,
    body: ApplyInterventionRequest,
    request: Request,
    actor: dict = Depends(require_authenticated),
) -> InterventionRecord:
    """Accept an intervention and trigger its external integration."""
    require_team_access(actor, team_id)

    team_history = data_store.team_history(team_id)
    if team_history is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    # Dispatch integration
    from api.services.intervention_store import _now
    applied_at = _now()
    integration = await _dispatch(
        intervention_id=body.intervention_id,
        team_id=team_id,
        team_name=team_history.team_name,
        actor_email=f"{actor['id']}@staging.local",
        actor_name=actor["name"],
        customization=body.customization,
        applied_at=applied_at,
    )

    record = intervention_store.apply(
        team_id=team_id,
        intervention_id=body.intervention_id,
        actor_id=actor["id"],
        actor_name=actor["name"],
        integration=integration,
        customization=body.customization,
    )

    audit_store.record(
        actor_id=actor["id"],
        actor_name=actor["name"],
        actor_role=actor["role"],
        action="apply_intervention",
        resource=team_id,
        detail=f"intervention={body.intervention_id} integration_status={integration.status}",
    )

    logger.info(
        "Intervention applied: team=%s intervention=%s actor=%s integration=%s status=%s",
        team_id, body.intervention_id, actor["id"], integration.integration, integration.status,
    )
    return record


@router.post("/{team_id}/dismiss", response_model=InterventionRecord)
def dismiss_intervention(
    team_id: str,
    body: DismissInterventionRequest,
    request: Request,
    actor: dict = Depends(require_authenticated),
) -> InterventionRecord:
    """Dismiss an intervention without executing any integration."""
    require_team_access(actor, team_id)

    record = intervention_store.dismiss(
        team_id=team_id,
        intervention_id=body.intervention_id,
        actor_id=actor["id"],
        actor_name=actor["name"],
    )

    audit_store.record(
        actor_id=actor["id"],
        actor_name=actor["name"],
        actor_role=actor["role"],
        action="dismiss_intervention",
        resource=team_id,
        detail=f"intervention={body.intervention_id}",
    )
    return record


@router.get("/{team_id}", response_model=list[InterventionRecord])
def get_team_interventions(
    team_id: str,
    actor: dict = Depends(require_authenticated),
) -> list[InterventionRecord]:
    """List all intervention records for a team."""
    require_team_access(actor, team_id)
    return intervention_store.records_for_team(team_id)


@router.get("/{team_id}/efficacy/{intervention_id}", response_model=EfficacyView)
def get_efficacy(
    team_id: str,
    intervention_id: str,
    actor: dict = Depends(require_authenticated),
) -> EfficacyView:
    """Return the before/after AFS trend for an applied intervention."""
    require_team_access(actor, team_id)

    record = intervention_store.latest_for_intervention(team_id, intervention_id)
    if record is None or record.action == "dismissed":
        raise HTTPException(
            status_code=404,
            detail=f"No accepted intervention '{intervention_id}' found for team '{team_id}'",
        )

    team_history = data_store.team_history(team_id)
    if team_history is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    applied_date = record.applied_at[:10]  # YYYY-MM-DD
    history = team_history.history

    before_points: list[EfficacyPoint] = []
    after_points:  list[EfficacyPoint] = []

    for pt in history:
        if pt.date < applied_date:
            before_points.append(EfficacyPoint(date=pt.date, afs=pt.afs, zone=pt.zone, phase="before"))
        elif pt.date >= applied_date:
            after_points.append(EfficacyPoint(date=pt.date, afs=pt.afs, zone=pt.zone, phase="after"))

    # Use last 13 days before + up to 14 days after
    before_window = before_points[-13:] if len(before_points) >= 13 else before_points
    after_window  = after_points[:14]

    before_avg = round(sum(p.afs for p in before_window) / len(before_window), 1) if before_window else 0.0
    after_avg  = round(sum(p.afs for p in after_window)  / len(after_window),  1) if after_window  else 0.0

    return EfficacyView(
        team_id=team_id,
        team_name=team_history.team_name,
        intervention_id=intervention_id,
        intervention_title=record.intervention_title,
        applied_at=record.applied_at,
        before_avg_afs=before_avg,
        after_avg_afs=after_avg,
        has_sufficient_data=len(after_window) >= 14,
        points=[*before_window, *after_window],
    )
