"""Team drill-down endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.dashboard import TeamHistory
from api.services.mock_data import store

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{team_id}/history", response_model=TeamHistory)
def get_team_history(team_id: str) -> TeamHistory:
    """Return 30-day AFS history and current features for a team."""
    result = store.team_history(team_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return result
