"""Unit tests for ml.inference.predictor — BurnoutPredictor."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from ml.inference.model_loader import ModelBundle
from ml.inference.predictor import BurnoutPredictor, PredictionResult

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_bundle(has_if: bool = True, has_lstm: bool = True) -> ModelBundle:
    """Build a ModelBundle with mock IF and/or LSTM."""
    bundle = ModelBundle()

    if has_if:
        mock_if = MagicMock()
        mock_if.predict_proba.return_value = np.array([[0.2, 0.5, 0.3]], dtype=np.float32)
        bundle.if_model = mock_if

    if has_lstm:
        mock_lstm = MagicMock()
        mock_lstm.predict_proba.return_value = np.array([[0.1, 0.6, 0.3]], dtype=np.float32)
        bundle.lstm_trainer = mock_lstm

    if has_if and has_lstm:
        mock_ensemble = MagicMock()
        mock_ensemble.predict_proba.return_value = np.array([[0.15, 0.55, 0.30]], dtype=np.float32)
        bundle.ensemble = mock_ensemble

    return bundle


_GREEN_FEATURES: dict[str, float] = {
    "calendar_density_score": 0.1,
    "after_hours_activity_index": 0.05,
    "context_switch_count": 0.1,
    "sprint_health_index": 0.9,
}

_RED_FEATURES: dict[str, float] = {
    "calendar_density_score": 0.9,
    "after_hours_activity_index": 0.8,
    "context_switch_count": 0.9,
    "sprint_health_index": 0.1,
}

_HISTORY_13: list[dict[str, float]] = [_GREEN_FEATURES] * 13


# ── Return type ───────────────────────────────────────────────────────────────


def test_predict_returns_prediction_result() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert isinstance(result, PredictionResult)


def test_prediction_result_has_required_fields() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert hasattr(result, "afs")
    assert hasattr(result, "resilience_zone")
    assert hasattr(result, "zone_label")
    assert hasattr(result, "probabilities")
    assert hasattr(result, "cold_start")
    assert hasattr(result, "model_version")


# ── AFS computation ───────────────────────────────────────────────────────────


def test_afs_in_valid_range() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert 0.0 <= result.afs <= 100.0


def test_afs_low_for_green_features() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert result.afs < 40.0


def test_afs_high_for_red_features() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_RED_FEATURES)
    assert result.afs > 60.0


# ── Zone label ────────────────────────────────────────────────────────────────


def test_zone_label_is_0_1_or_2() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert result.zone_label in {0, 1, 2}


def test_zone_name_matches_label() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    label_to_name = {0: "green", 1: "yellow", 2: "red"}
    assert result.resilience_zone == label_to_name[result.zone_label]


# ── Probabilities ─────────────────────────────────────────────────────────────


def test_probabilities_have_three_zones() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    assert set(result.probabilities.keys()) == {"green", "yellow", "red"}


def test_probabilities_sum_to_one() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES)
    total = sum(result.probabilities.values())
    assert abs(total - 1.0) < 0.01


# ── Cold-start vs warm-start ──────────────────────────────────────────────────


def test_no_history_is_cold_start() -> None:
    predictor = BurnoutPredictor(_make_bundle(has_lstm=False))
    result = predictor.predict(_GREEN_FEATURES, history=None)
    assert result.cold_start is True


def test_full_history_with_ensemble_is_warm_start() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    result = predictor.predict(_GREEN_FEATURES, history=_HISTORY_13)
    assert result.cold_start is False


def test_partial_history_is_cold_start() -> None:
    predictor = BurnoutPredictor(_make_bundle())
    # Only 5 days of history — not enough for LSTM (need 13)
    result = predictor.predict(_GREEN_FEATURES, history=[_GREEN_FEATURES] * 5)
    assert result.cold_start is True


def test_ensemble_predict_proba_called_on_warm_start() -> None:
    bundle = _make_bundle()
    predictor = BurnoutPredictor(bundle)
    predictor.predict(_GREEN_FEATURES, history=_HISTORY_13)
    bundle.ensemble.predict_proba.assert_called_once()  # type: ignore[union-attr]


def test_if_predict_proba_called_on_cold_start() -> None:
    bundle = _make_bundle(has_lstm=False)
    predictor = BurnoutPredictor(bundle)
    predictor.predict(_GREEN_FEATURES, history=None)
    bundle.if_model.predict_proba.assert_called_once()  # type: ignore[union-attr]


# ── AFS-only fallback (no IF, no LSTM) ───────────────────────────────────────


def test_afs_only_fallback_is_cold_start() -> None:
    empty_bundle = ModelBundle()
    predictor = BurnoutPredictor(empty_bundle)
    result = predictor.predict(_GREEN_FEATURES)
    assert result.cold_start is True


def test_afs_only_fallback_returns_valid_zone() -> None:
    empty_bundle = ModelBundle()
    predictor = BurnoutPredictor(empty_bundle)
    result = predictor.predict(_GREEN_FEATURES)
    assert result.resilience_zone in {"green", "yellow", "red"}
