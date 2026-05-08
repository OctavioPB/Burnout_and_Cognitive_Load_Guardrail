"""Unit tests for ml.training.baseline — RuleBasedBaseline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.training.baseline import RuleBasedBaseline, _GREEN_THRESHOLDS, _RED_THRESHOLDS
from ml.training.features import RAW_FEATURE_COLS, ResilienceZone
from ml.training.synthetic import SyntheticDataGenerator
from ml.training.dataset import temporal_split


# ── predict_one — zone boundaries ─────────────────────────────────────────────


def test_predict_one_all_low_stress_is_green() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.10,
        "after_hours_activity_index": 0.05,
        "context_switch_count": 0.10,
        "sprint_health_index": 0.90,
    })
    assert zone == ResilienceZone.GREEN


def test_predict_one_high_calendar_density_triggers_red() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.70,
        "after_hours_activity_index": 0.05,
        "context_switch_count": 0.10,
        "sprint_health_index": 0.90,
    })
    assert zone == ResilienceZone.RED


def test_predict_one_high_after_hours_triggers_red() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.10,
        "after_hours_activity_index": 0.55,
        "context_switch_count": 0.10,
        "sprint_health_index": 0.90,
    })
    assert zone == ResilienceZone.RED


def test_predict_one_high_context_switch_triggers_red() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.10,
        "after_hours_activity_index": 0.05,
        "context_switch_count": 0.65,
        "sprint_health_index": 0.90,
    })
    assert zone == ResilienceZone.RED


def test_predict_one_low_sprint_health_triggers_red() -> None:
    """Low SHI is bad (inverted scale) — should trigger Red."""
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.10,
        "after_hours_activity_index": 0.05,
        "context_switch_count": 0.10,
        "sprint_health_index": 0.20,
    })
    assert zone == ResilienceZone.RED


def test_predict_one_mid_range_is_yellow() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": 0.45,
        "after_hours_activity_index": 0.25,
        "context_switch_count": 0.40,
        "sprint_health_index": 0.55,
    })
    assert zone == ResilienceZone.YELLOW


def test_predict_one_missing_keys_not_red() -> None:
    """Empty dict: SHI defaults to 0.5 (neutral), not below Red threshold → not Red."""
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({})
    assert zone != ResilienceZone.RED


def test_predict_one_none_values_default_to_zero() -> None:
    baseline = RuleBasedBaseline()
    zone = baseline.predict_one({
        "calendar_density_score": None,
        "after_hours_activity_index": None,
        "context_switch_count": None,
        "sprint_health_index": None,
    })
    assert zone in {ResilienceZone.GREEN, ResilienceZone.YELLOW}


# ── predict — batch ───────────────────────────────────────────────────────────


def test_predict_returns_int32_array() -> None:
    baseline = RuleBasedBaseline()
    X = np.zeros((10, len(RAW_FEATURE_COLS)), dtype=np.float32)
    y = baseline.predict(X)
    assert y.dtype == np.int32


def test_predict_output_shape_matches_input() -> None:
    baseline = RuleBasedBaseline()
    X = np.random.default_rng(0).random((50, len(RAW_FEATURE_COLS))).astype(np.float32)
    y = baseline.predict(X)
    assert y.shape == (50,)


def test_predict_values_in_valid_range() -> None:
    baseline = RuleBasedBaseline()
    X = np.random.default_rng(42).random((100, len(RAW_FEATURE_COLS))).astype(np.float32)
    y = baseline.predict(X)
    assert set(np.unique(y)).issubset({0, 1, 2})


def test_predict_wrong_feature_count_raises() -> None:
    baseline = RuleBasedBaseline()
    X = np.zeros((5, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="features"):
        baseline.predict(X)


def test_predict_all_zero_features_not_red() -> None:
    """All-zero features: SHI=0.0 ORs to 0.5 default, not below Red threshold."""
    baseline = RuleBasedBaseline()
    X = np.zeros((5, len(RAW_FEATURE_COLS)), dtype=np.float32)
    y = baseline.predict(X)
    assert (y != ResilienceZone.RED.label).all()


# ── evaluate ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def split():
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=30, n_days=60)
    return temporal_split(df)


def test_evaluate_returns_required_keys(split) -> None:
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    assert "accuracy" in metrics
    assert "per_class" in metrics
    assert "n_samples" in metrics
    assert "model" in metrics


def test_evaluate_accuracy_between_zero_and_one(split) -> None:
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    assert 0.0 <= metrics["accuracy"] <= 1.0


def test_evaluate_per_class_has_all_zones(split) -> None:
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    assert set(metrics["per_class"].keys()) == {"green", "yellow", "red"}


def test_evaluate_per_class_metrics_in_valid_range(split) -> None:
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    for zone_metrics in metrics["per_class"].values():
        assert 0.0 <= zone_metrics["precision"] <= 1.0
        assert 0.0 <= zone_metrics["recall"] <= 1.0
        assert 0.0 <= zone_metrics["f1"] <= 1.0
        assert zone_metrics["support"] >= 0


def test_evaluate_n_samples_matches_input(split) -> None:
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    assert metrics["n_samples"] == len(split.y_train)


def test_evaluate_writes_json_to_path(split, tmp_path: Path) -> None:
    baseline = RuleBasedBaseline()
    output = tmp_path / "baseline" / "metrics.json"
    baseline.evaluate(split.X_test, split.y_test, output_path=output)
    assert output.exists()
    data = json.loads(output.read_text())
    assert "accuracy" in data


def test_evaluate_no_path_does_not_create_file(split, tmp_path: Path) -> None:
    baseline = RuleBasedBaseline()
    baseline.evaluate(split.X_test, split.y_test, output_path=None)
    assert not any(tmp_path.iterdir())


# ── Custom thresholds ─────────────────────────────────────────────────────────


def test_custom_thresholds_override_defaults() -> None:
    strict = RuleBasedBaseline(
        red_thresholds={**_RED_THRESHOLDS, "calendar_density_score": 0.10},
        green_thresholds=_GREEN_THRESHOLDS,
    )
    permissive = RuleBasedBaseline()
    features = {
        "calendar_density_score": 0.15,
        "after_hours_activity_index": 0.05,
        "context_switch_count": 0.10,
        "sprint_health_index": 0.90,
    }
    assert strict.predict_one(features) == ResilienceZone.RED
    assert permissive.predict_one(features) == ResilienceZone.GREEN


# ── Red zone precision — safety-first invariant ───────────────────────────────


def test_red_zone_recall_reasonable_on_synthetic_data(split) -> None:
    """Baseline should catch most genuine Red-zone teams (recall > 0.5)."""
    baseline = RuleBasedBaseline()
    metrics = baseline.evaluate(split.X_train, split.y_train)
    assert metrics["per_class"]["red"]["recall"] >= 0.5, (
        f"Red recall too low: {metrics['per_class']['red']['recall']:.3f}"
    )
