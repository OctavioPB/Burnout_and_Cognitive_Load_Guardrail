"""Audit log endpoint — HR Admin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.schemas.interventions import AuditLogEntry
from api.services.intervention_store import audit_store
from api.dependencies import require_hr_admin

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogEntry])
def get_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    _actor: dict = Depends(require_hr_admin),
) -> list[AuditLogEntry]:
    """Return audit log entries, most recent first.  HR Admin role required."""
    return audit_store.entries(limit=limit)
