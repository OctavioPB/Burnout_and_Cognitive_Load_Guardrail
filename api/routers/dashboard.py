"""Dashboard summary and team list endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.schemas.dashboard import DashboardSummary, TeamCard
from api.services.mock_data import store

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary() -> DashboardSummary:
    """Return org-wide zone distribution and per-department breakdown."""
    return store.summary()


@router.get("/teams", response_model=list[TeamCard])
def get_teams(
    department: str | None = Query(default=None, description="Filter by department name"),
) -> list[TeamCard]:
    """Return all team cards, sorted by AFS descending (highest risk first)."""
    return store.teams(department=department)
