"""Team drill-down endpoints — RBAC enforced."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import require_authenticated, require_team_access
from api.schemas.dashboard import TeamHistory
from api.services.mock_data import store

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{team_id}/history", response_model=TeamHistory)
def get_team_history(
    team_id: str,
    request: Request,
    actor: dict[str, Any] = Depends(require_authenticated),
) -> TeamHistory:
    """Return 30-day AFS history and current features for a team.

    RBAC: team_manager can only access their own team_id.
    """
    require_team_access(actor, team_id)

    result = store.team_history(team_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return result
