"""Pydantic request / response schemas for the inference API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

# ── Request ───────────────────────────────────────────────────────────────────


class DayFeatures(BaseModel):
    """Feature vector for a single team-day (used both in current and history)."""

    calendar_density_score: Annotated[float, Field(ge=0.0, le=1.0)]
    after_hours_activity_index: Annotated[float, Field(ge=0.0, le=1.0)]
    context_switch_count: Annotated[float, Field(ge=0.0, le=1.0)]
    sprint_health_index: Annotated[float, Field(ge=0.0, le=1.0)]


class PredictRequest(BaseModel):
    """Single-team prediction request.

    ``history`` is optional.  When provided with ≥ 13 entries the service uses
    the full ensemble (IF + LSTM + AFS).  Fewer entries trigger cold-start mode
    (IF + AFS only).
    """

    team_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)
    date_utc: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    calendar_density_score: Annotated[float, Field(ge=0.0, le=1.0)]
    after_hours_activity_index: Annotated[float, Field(ge=0.0, le=1.0)]
    context_switch_count: Annotated[float, Field(ge=0.0, le=1.0)]
    sprint_health_index: Annotated[float, Field(ge=0.0, le=1.0)]

    # Optional: up to 13 prior days for LSTM context (oldest → newest)
    history: list[DayFeatures] | None = Field(default=None, max_length=13)

    @model_validator(mode="after")
    def validate_history_order(self) -> PredictRequest:
        """Silently accepted — history ordering responsibility is on the caller."""
        return self

    def current_features(self) -> dict[str, float]:
        return {
            "calendar_density_score": self.calendar_density_score,
            "after_hours_activity_index": self.after_hours_activity_index,
            "context_switch_count": self.context_switch_count,
            "sprint_health_index": self.sprint_health_index,
        }


class BatchPredictRequest(BaseModel):
    """Batch prediction request for multiple teams in a single call."""

    items: list[PredictRequest] = Field(..., min_length=1, max_length=500)


# ── Response ──────────────────────────────────────────────────────────────────


class Intervention(BaseModel):
    """A single suggested HR intervention."""

    id: str
    title: str
    description: str


class PredictResponse(BaseModel):
    """Prediction result for a single team-day."""

    team_id: str
    workspace_id: str
    date_utc: str

    afs: float = Field(ge=0.0, le=100.0)
    resilience_zone: str  # "green" | "yellow" | "red"
    zone_label: int = Field(ge=0, le=2)

    probabilities: dict[str, float]  # {"green": p, "yellow": p, "red": p}

    interventions: list[Intervention] = Field(default_factory=list)
    cold_start: bool = False
    model_version: str


class BatchPredictResponse(BaseModel):
    """Batch prediction results."""

    results: list[PredictResponse]
    n_items: int
    model_version: str


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Liveness and model status response."""

    status: str          # "ok" | "degraded"
    model_version: str
    models_loaded: dict[str, bool]   # {"isolation_forest": T, "lstm": T}
    message: str = ""
