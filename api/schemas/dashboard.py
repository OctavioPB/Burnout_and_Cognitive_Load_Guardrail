"""Pydantic response models for the dashboard API."""

from __future__ import annotations

from pydantic import BaseModel


class FeatureScores(BaseModel):
    calendar_density_score: float
    after_hours_activity_index: float
    context_switch_count: float
    sprint_health_index: float


class TeamCard(BaseModel):
    team_id: str
    team_name: str
    department: str
    zone: str
    zone_label: int
    afs: float
    features: FeatureScores
    has_active_alert: bool


class DeptSummary(BaseModel):
    department: str
    total: int
    green: int
    yellow: int
    red: int


class DashboardSummary(BaseModel):
    total_teams: int
    green: int
    yellow: int
    red: int
    active_alerts: int
    departments: list[DeptSummary]


class DayPoint(BaseModel):
    date: str
    afs: float
    zone: str
    calendar_density_score: float
    after_hours_activity_index: float
    context_switch_count: float
    sprint_health_index: float


class InterventionItem(BaseModel):
    id: str
    title: str
    description: str


class TeamHistory(BaseModel):
    team_id: str
    team_name: str
    department: str
    zone: str
    afs: float
    features: FeatureScores
    history: list[DayPoint]
    interventions: list[InterventionItem]


class AlertRecord(BaseModel):
    alert_id: str
    team_id: str
    team_name: str
    department: str
    workspace_id: str
    trigger_date: str
    consecutive_red_days: int
    interventions: list[InterventionItem]
