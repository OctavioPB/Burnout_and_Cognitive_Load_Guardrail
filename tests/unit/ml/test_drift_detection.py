"""Unit tests for ml.training.drift_detection."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ml.training.dataset import temporal_split
from ml.training.drift_detection import (
    check_drift,
    compute_feature_fingerprint,
    load_fingerprint,
    save_fingerprint,
)
from ml.training.features import RAW_FEATURE_COLS
from ml.training.synthetic import SyntheticDataGenerator


@pytest.fixture(scope="module")
def X_train() -> np.ndarray:
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=30, n_days=60)
    split = temporal_split(df)
    return split.X_train


# ── compute_feature_fingerprint ───────────────────────────────────────────────


def test_fingerprint_has_n_samples(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    assert fp["n_samples"] == len(X_train)


def test_fingerprint_has_n_features(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    assert fp["n_features"] == X_train.shape[1]


def test_fingerprint_has_all_feature_names(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    assert set(fp["features"].keys()) == set(RAW_FEATURE_COLS)


def test_fingerprint_per_feature_has_required_keys(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    required = {"mean", "std", "min", "max", "percentiles"}
    for name, stats in fp["features"].items():
        assert required.issubset(set(stats.keys())), f"Missing keys for {name}"


def test_fingerprint_percentiles_keys(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    first_feature = next(iter(fp["features"].values()))
    pcts = first_feature["percentiles"]
    assert set(pcts.keys()) == {"5", "25", "50", "75", "95"}


def test_fingerprint_mean_in_valid_range(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    for name, stats in fp["features"].items():
        assert 0.0 <= stats["mean"] <= 1.0, f"{name}: mean={stats['mean']}"


def test_fingerprint_min_max_bounds(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    for stats in fp["features"].values():
        assert stats["min"] <= stats["mean"] <= stats["max"]


def test_fingerprint_custom_feature_names() -> None:
    X = np.random.default_rng(0).random((100, 2)).astype(np.float32)
    fp = compute_feature_fingerprint(X, feature_names=["feat_a", "feat_b"])
    assert set(fp["features"].keys()) == {"feat_a", "feat_b"}


# ── save / load fingerprint ───────────────────────────────────────────────────


def test_save_load_round_trip(X_train: np.ndarray, tmp_path: Path) -> None:
    fp = compute_feature_fingerprint(X_train)
    path = tmp_path / "fingerprint.json"
    save_fingerprint(fp, path)
    loaded = load_fingerprint(path)
    assert loaded["n_samples"] == fp["n_samples"]
    assert set(loaded["features"].keys()) == set(fp["features"].keys())


def test_save_creates_parent_dirs(X_train: np.ndarray, tmp_path: Path) -> None:
    fp = compute_feature_fingerprint(X_train)
    path = tmp_path / "nested" / "dir" / "fingerprint.json"
    save_fingerprint(fp, path)
    assert path.exists()


def test_saved_fingerprint_is_valid_json(X_train: np.ndarray, tmp_path: Path) -> None:
    fp = compute_feature_fingerprint(X_train)
    path = tmp_path / "fp.json"
    save_fingerprint(fp, path)
    # Should be loadable by standard json module
    data = json.loads(path.read_text())
    assert "features" in data


# ── check_drift ───────────────────────────────────────────────────────────────


def test_no_drift_on_same_distribution(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    # Use a different sample from the same distribution
    X_same = SyntheticDataGenerator(seed=99).generate_dataframe(
        n_teams=30, n_days=60
    )[RAW_FEATURE_COLS].to_numpy(dtype=np.float32)
    report = check_drift(X_same, fp, threshold=3.0)
    assert not report["any_drift"], (
        f"Expected no drift; drifted: {report['drifted_features']}"
    )


def test_drift_detected_on_shifted_distribution(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    # Shift all features by +0.5 — should be way outside the training distribution
    X_shifted = np.clip(X_train + 0.5, 0.0, 1.0)
    report = check_drift(X_shifted, fp, threshold=2.0)
    assert report["any_drift"], "Expected drift on shifted distribution"
    assert len(report["drifted_features"]) > 0


def test_drift_report_has_required_keys(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    report = check_drift(X_train, fp)
    assert set(report.keys()) == {"any_drift", "drifted_features", "drift_details", "threshold"}


def test_drift_details_z_score_is_float(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    report = check_drift(X_train, fp)
    for name, detail in report["drift_details"].items():
        assert isinstance(detail["z_score"], float), f"{name}: z_score not float"


def test_drift_threshold_respected(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    # Very tight threshold → likely to flag drift
    report_tight = check_drift(X_train + 0.1, fp, threshold=0.5)
    # Very loose threshold → unlikely to flag drift
    report_loose = check_drift(X_train + 0.1, fp, threshold=100.0)
    assert report_loose["threshold"] == 100.0
    # Tight should flag more (or equal) drifted features than loose
    assert len(report_tight["drifted_features"]) >= len(report_loose["drifted_features"])


def test_drift_any_drift_matches_drifted_features(X_train: np.ndarray) -> None:
    fp = compute_feature_fingerprint(X_train)
    report = check_drift(X_train, fp)
    assert report["any_drift"] == (len(report["drifted_features"]) > 0)


def test_drift_no_crash_on_constant_feature() -> None:
    """A constant feature (std=0) should not cause division by zero."""
    X_const = np.ones((50, 4), dtype=np.float32) * 0.5
    fp = compute_feature_fingerprint(X_const)
    report = check_drift(X_const, fp)
    assert "any_drift" in report
