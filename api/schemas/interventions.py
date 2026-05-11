"""Pydantic models for interventions, efficacy, and audit log."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Intervention actions ──────────────────────────────────────────────────────

InterventionAction = Literal["accepted", "dismissed", "customized"]
IntegrationStatus  = Literal["pending", "success", "failed", "skipped"]


class ApplyInterventionRequest(BaseModel):
    intervention_id: str = Field(..., min_length=1)
    customization: str | None = None  # user-written message for async_first_week


class DismissInterventionRequest(BaseModel):
    intervention_id: str = Field(..., min_length=1)


class IntegrationResult(BaseModel):
    integration: str                # "google_calendar" | "jira" | "slack" | "none"
    status: IntegrationStatus
    external_id: str | None = None  # created resource ID
    detail: str = ""


class InterventionRecord(BaseModel):
    record_id: str
    team_id: str
    intervention_id: str
    intervention_title: str
    action: InterventionAction
    actor_id: str
    actor_name: str
    applied_at: str             # ISO datetime
    customization: str | None = None
    integration: IntegrationResult


# ── Efficacy ──────────────────────────────────────────────────────────────────

class EfficacyPoint(BaseModel):
    date: str
    afs: float
    zone: str
    phase: Literal["before", "after"]


class EfficacyView(BaseModel):
    team_id: str
    team_name: str
    intervention_id: str
    intervention_title: str
    applied_at: str
    before_avg_afs: float
    after_avg_afs: float
    has_sufficient_data: bool   # True if ≥ 14 days of post-intervention data exist
    points: list[EfficacyPoint]


# ── Audit log ─────────────────────────────────────────────────────────────────

AuditAction = Literal[
    "view_dashboard",
    "view_team",
    "view_alerts",
    "view_audit",
    "apply_intervention",
    "dismiss_intervention",
]


class AuditLogEntry(BaseModel):
    log_id: str
    actor_id: str
    actor_name: str
    actor_role: str
    action: AuditAction
    resource: str               # team_id, "dashboard", "alerts", etc.
    timestamp: str              # ISO datetime
    detail: str = ""
