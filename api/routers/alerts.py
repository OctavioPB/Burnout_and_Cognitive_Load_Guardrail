"""Alert feed endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.schemas.dashboard import AlertRecord
from api.services.mock_data import store

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRecord])
def get_alerts(
    department: str | None = Query(default=None, description="Filter by department"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AlertRecord]:
    """Return Red Zone alerts sorted by trigger date descending."""
    return store.alerts(department=department, limit=limit)
