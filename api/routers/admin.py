"""Admin endpoints — HR Admin only.

Provides database reset and custom seed operations for demo / staging
environments.  All endpoints require the hr_admin role.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.dependencies import require_hr_admin
from api.services.mock_data import SeedConfig, store

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Request / response models ─────────────────────────────────────────────────

class AdminTeamEntry(BaseModel):
    team_id: str   = Field(..., examples=["T-01"])
    team_name: str = Field(..., examples=["Frontend Engineering"])
    department: str = Field(..., examples=["Engineering"])


class AdminSeedRequest(BaseModel):
    teams: list[AdminTeamEntry] = Field(..., min_length=1)
    stress_profile: Literal["low", "mixed", "high"] = "mixed"
    history_days: Literal[7, 14, 30] = 30


class AdminActionResponse(BaseModel):
    message: str
    team_count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/reset", response_model=AdminActionResponse)
def reset_store(
    _actor: dict[str, Any] = Depends(require_hr_admin),
) -> AdminActionResponse:
    """Restore the default 12-team dataset with the original seeded trajectories."""
    store.reset()
    return AdminActionResponse(
        message="Dataset reset to defaults (12 teams, mixed stress profile, 30-day history).",
        team_count=12,
    )


@router.post("/seed", response_model=AdminActionResponse)
def seed_store(
    body: AdminSeedRequest,
    _actor: dict[str, Any] = Depends(require_hr_admin),
) -> AdminActionResponse:
    """Rebuild the dataset from a custom team roster and stress configuration."""
    config = SeedConfig(
        teams=[t.model_dump() for t in body.teams],
        stress_profile=body.stress_profile,
        history_days=body.history_days,
    )
    store.reset(config)
    return AdminActionResponse(
        message=(
            f"Dataset seeded with {len(body.teams)} team(s), "
            f"{body.stress_profile} stress profile, {body.history_days}-day history."
        ),
        team_count=len(body.teams),
    )
