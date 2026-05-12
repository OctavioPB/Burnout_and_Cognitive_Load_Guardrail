"""Unit tests for ml.inference.schemas — request/response Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ml.inference.schemas import (
    BatchPredictRequest,
    DayFeatures,
    HealthResponse,
    PredictRequest,
    PredictResponse,
)

# ── DayFeatures ───────────────────────────────────────────────────────────────


def test_day_features_valid() -> None:
    f = DayFeatures(
        calendar_density_score=0.3,
        after_hours_activity_index=0.2,
        context_switch_count=0.5,
        sprint_health_index=0.8,
    )
    assert f.calendar_density_score == 0.3


def test_day_features_rejects_above_one() -> None:
    with pytest.raises(ValidationError):
        DayFeatures(
            calendar_density_score=1.1,
            after_hours_activity_index=0.0,
            context_switch_count=0.0,
            sprint_health_index=0.5,
        )


def test_day_features_rejects_below_zero() -> None:
    with pytest.raises(ValidationError):
        DayFeatures(
            calendar_density_score=0.5,
            after_hours_activity_index=-0.1,
            context_switch_count=0.0,
            sprint_health_index=0.5,
        )


# ── PredictRequest ────────────────────────────────────────────────────────────


def _minimal_request(**kwargs) -> dict:
    base = {
        "team_id": "T-1",
        "workspace_id": "W-1",
        "date_utc": "2024-01-15",
        "calendar_density_score": 0.4,
        "after_hours_activity_index": 0.3,
        "context_switch_count": 0.5,
        "sprint_health_index": 0.7,
    }
    base.update(kwargs)
    return base


def test_predict_request_valid_no_history() -> None:
    req = PredictRequest(**_minimal_request())
    assert req.history is None


def test_predict_request_valid_with_history() -> None:
    history = [
        {
            "calendar_density_score": 0.3,
            "after_hours_activity_index": 0.2,
            "context_switch_count": 0.4,
            "sprint_health_index": 0.8,
        }
    ] * 13
    req = PredictRequest(**_minimal_request(history=history))
    assert req.history is not None
    assert len(req.history) == 13


def test_predict_request_invalid_date_format() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(**_minimal_request(date_utc="15-01-2024"))


def test_predict_request_empty_team_id_raises() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(**_minimal_request(team_id=""))


def test_predict_request_feature_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(**_minimal_request(calendar_density_score=1.5))


def test_predict_request_current_features_returns_dict() -> None:
    req = PredictRequest(**_minimal_request())
    feat = req.current_features()
    assert set(feat.keys()) == {
        "calendar_density_score",
        "after_hours_activity_index",
        "context_switch_count",
        "sprint_health_index",
    }


def test_predict_request_history_max_13() -> None:
    history_14 = [
        {
            "calendar_density_score": 0.3,
            "after_hours_activity_index": 0.2,
            "context_switch_count": 0.4,
            "sprint_health_index": 0.8,
        }
    ] * 14
    with pytest.raises(ValidationError):
        PredictRequest(**_minimal_request(history=history_14))


# ── PredictResponse ───────────────────────────────────────────────────────────


def _valid_response(**kwargs) -> dict:
    base = {
        "team_id": "T-1",
        "workspace_id": "W-1",
        "date_utc": "2024-01-15",
        "afs": 52.3,
        "resilience_zone": "yellow",
        "zone_label": 1,
        "probabilities": {"green": 0.1, "yellow": 0.7, "red": 0.2},
        "model_version": "v1.0",
    }
    base.update(kwargs)
    return base


def test_predict_response_valid() -> None:
    resp = PredictResponse(**_valid_response())
    assert resp.resilience_zone == "yellow"
    assert resp.cold_start is False
    assert resp.interventions == []


def test_predict_response_afs_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        PredictResponse(**_valid_response(afs=101.0))


def test_predict_response_zone_label_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        PredictResponse(**_valid_response(zone_label=3))


# ── BatchPredictRequest ───────────────────────────────────────────────────────


def test_batch_request_empty_items_raises() -> None:
    with pytest.raises(ValidationError):
        BatchPredictRequest(items=[])


def test_batch_request_valid() -> None:
    items = [PredictRequest(**_minimal_request(team_id=f"T-{i}")) for i in range(3)]
    req = BatchPredictRequest(items=items)
    assert req.items[0].team_id == "T-0"


# ── HealthResponse ────────────────────────────────────────────────────────────


def test_health_response_ok() -> None:
    h = HealthResponse(
        status="ok",
        model_version="v1.0",
        models_loaded={"isolation_forest": True, "lstm": True},
    )
    assert h.status == "ok"
    assert h.message == ""


def test_health_response_degraded() -> None:
    h = HealthResponse(
        status="degraded",
        model_version="v1.0",
        models_loaded={"isolation_forest": False, "lstm": False},
        message="Models not loaded",
    )
    assert h.status == "degraded"
