"""Unit tests for ml.evaluation.evaluate — classification_metrics and train_and_evaluate."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ml.evaluation.evaluate import classification_metrics, train_and_evaluate


# ── classification_metrics ────────────────────────────────────────────────────


def test_metrics_has_required_keys() -> None:
    y_true = np.array([0, 1, 2, 0, 1, 2], dtype=np.int32)
    y_pred = np.array([0, 1, 2, 0, 1, 2], dtype=np.int32)
    m = classification_metrics(y_true, y_pred)
    assert "accuracy" in m
    assert "per_class" in m
    assert "n_samples" in m


def test_metrics_per_class_has_all_zones() -> None:
    y = np.array([0, 1, 2], dtype=np.int32)
    m = classification_metrics(y, y)
    assert set(m["per_class"].keys()) == {"green", "yellow", "red"}


def test_metrics_perfect_predictions_give_accuracy_one() -> None:
    y = np.array([0, 1, 2, 0, 1, 2, 2, 0], dtype=np.int32)
    m = classification_metrics(y, y)
    assert m["accuracy"] == pytest.approx(1.0)


def test_metrics_perfect_predictions_give_f1_one() -> None:
    y = np.array([0, 1, 2, 0, 1, 2], dtype=np.int32)
    m = classification_metrics(y, y)
    for zone_m in m["per_class"].values():
        assert zone_m["f1"] == pytest.approx(1.0)


def test_metrics_all_wrong_green_gives_zero_precision() -> None:
    # Predict only red, true only green
    y_true = np.zeros(10, dtype=np.int32)   # all green
    y_pred = np.full(10, 2, dtype=np.int32)  # all red
    m = classification_metrics(y_true, y_pred)
    assert m["per_class"]["green"]["precision"] == pytest.approx(0.0)
    assert m["per_class"]["red"]["recall"] == pytest.approx(0.0)


def test_metrics_accuracy_between_zero_and_one() -> None:
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 3, size=100).astype(np.int32)
    y_pred = rng.integers(0, 3, size=100).astype(np.int32)
    m = classification_metrics(y_true, y_pred)
    assert 0.0 <= m["accuracy"] <= 1.0


def test_metrics_n_samples_matches_input() -> None:
    y = np.array([0, 1, 2, 0], dtype=np.int32)
    m = classification_metrics(y, y)
    assert m["n_samples"] == 4


def test_metrics_fpr_in_valid_range() -> None:
    rng = np.random.default_rng(7)
    y_true = rng.integers(0, 3, size=50).astype(np.int32)
    y_pred = rng.integers(0, 3, size=50).astype(np.int32)
    m = classification_metrics(y_true, y_pred)
    for zone_m in m["per_class"].values():
        assert 0.0 <= zone_m["fpr"] <= 1.0


def test_metrics_support_sums_to_n_samples() -> None:
    y = np.array([0, 0, 1, 2, 2, 2], dtype=np.int32)
    m = classification_metrics(y, y)
    total_support = sum(z["support"] for z in m["per_class"].values())
    assert total_support == m["n_samples"]


# ── train_and_evaluate ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def eval_result(tmp_path_factory) -> dict:
    """Run a fast evaluation with minimal data once per test session."""
    out_dir = tmp_path_factory.mktemp("models")
    return train_and_evaluate(
        n_teams=20,
        n_days=40,
        seed=42,
        output_dir=out_dir,
        lstm_max_epochs=5,
        lstm_patience=3,
    )


def test_eval_returns_required_top_level_keys(eval_result: dict) -> None:
    assert {"seed", "n_teams", "n_days", "split_summary", "isolation_forest",
            "lstm", "ensemble"}.issubset(eval_result.keys())


def test_eval_ensemble_has_accuracy(eval_result: dict) -> None:
    assert "accuracy" in eval_result["ensemble"]


def test_eval_ensemble_accuracy_between_zero_and_one(eval_result: dict) -> None:
    acc = eval_result["ensemble"]["accuracy"]
    assert 0.0 <= acc <= 1.0


def test_eval_metrics_json_written(eval_result: dict, tmp_path: Path) -> None:
    out_dir = tmp_path / "models"
    train_and_evaluate(n_teams=10, n_days=30, seed=1, output_dir=out_dir, lstm_max_epochs=2)
    assert (out_dir / "metrics.json").exists()


def test_eval_fingerprint_json_written(eval_result: dict, tmp_path: Path) -> None:
    out_dir = tmp_path / "models2"
    train_and_evaluate(n_teams=10, n_days=30, seed=2, output_dir=out_dir, lstm_max_epochs=2)
    assert (out_dir / "fingerprint.json").exists()


def test_eval_if_model_saved(tmp_path: Path) -> None:
    out_dir = tmp_path / "models3"
    train_and_evaluate(n_teams=10, n_days=30, seed=3, output_dir=out_dir, lstm_max_epochs=2)
    assert (out_dir / "isolation_forest.joblib").exists()
