"""Unit tests for ml.training.isolation_forest — BurnoutIsolationForest."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ml.training.features import RAW_FEATURE_COLS
from ml.training.isolation_forest import BurnoutIsolationForest
from ml.training.synthetic import SyntheticDataGenerator
from ml.training.dataset import temporal_split


@pytest.fixture(scope="module")
def fitted_model() -> BurnoutIsolationForest:
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=30, n_days=30)
    split = temporal_split(df)
    model = BurnoutIsolationForest()
    model.fit(split.X_train)
    return model


@pytest.fixture(scope="module")
def X_test() -> np.ndarray:
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=30, n_days=30)
    split = temporal_split(df)
    return split.X_test


# ── Fit ───────────────────────────────────────────────────────────────────────


def test_fit_returns_self() -> None:
    X = np.random.default_rng(0).random((50, 4)).astype(np.float32)
    model = BurnoutIsolationForest()
    result = model.fit(X)
    assert result is model


def test_predict_before_fit_raises() -> None:
    model = BurnoutIsolationForest()
    X = np.zeros((5, 4), dtype=np.float32)
    with pytest.raises(RuntimeError, match="fitted"):
        model.predict(X)


def test_anomaly_score_before_fit_raises() -> None:
    model = BurnoutIsolationForest()
    X = np.zeros((5, 4), dtype=np.float32)
    with pytest.raises(RuntimeError, match="fitted"):
        model.anomaly_score(X)


# ── anomaly_score ─────────────────────────────────────────────────────────────


def test_anomaly_score_range(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    scores = fitted_model.anomaly_score(X_test)
    assert scores.min() >= 0.0
    assert scores.max() <= 1.0


def test_anomaly_score_dtype(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    scores = fitted_model.anomaly_score(X_test)
    assert scores.dtype == np.float32


def test_anomaly_score_shape(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    scores = fitted_model.anomaly_score(X_test)
    assert scores.shape == (len(X_test),)


def test_high_stress_features_score_higher_than_low() -> None:
    """Red-zone features should produce higher anomaly scores than green-zone features."""
    model = BurnoutIsolationForest()
    # Green-zone: low stress
    X_train = np.random.default_rng(0).random((200, 4)).astype(np.float32) * 0.3
    model.fit(X_train)

    X_green = np.array([[0.05, 0.05, 0.05, 0.95]], dtype=np.float32)
    X_red = np.array([[0.95, 0.90, 0.95, 0.05]], dtype=np.float32)
    assert model.anomaly_score(X_red)[0] > model.anomaly_score(X_green)[0]


# ── predict_proba ─────────────────────────────────────────────────────────────


def test_predict_proba_shape(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    proba = fitted_model.predict_proba(X_test)
    assert proba.shape == (len(X_test), 3)


def test_predict_proba_sums_to_one(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    proba = fitted_model.predict_proba(X_test)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_predict_proba_all_non_negative(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    proba = fitted_model.predict_proba(X_test)
    assert (proba >= 0.0).all()


def test_predict_proba_dtype(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    proba = fitted_model.predict_proba(X_test)
    assert proba.dtype == np.float32


# ── predict ───────────────────────────────────────────────────────────────────


def test_predict_values_in_valid_range(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    y = fitted_model.predict(X_test)
    assert set(np.unique(y)).issubset({0, 1, 2})


def test_predict_dtype(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    y = fitted_model.predict(X_test)
    assert y.dtype == np.int32


def test_predict_shape(fitted_model: BurnoutIsolationForest, X_test: np.ndarray) -> None:
    y = fitted_model.predict(X_test)
    assert y.shape == (len(X_test),)


# ── Serialization ─────────────────────────────────────────────────────────────


def test_save_load_round_trip(fitted_model: BurnoutIsolationForest, X_test: np.ndarray, tmp_path: Path) -> None:
    path = tmp_path / "if_model.joblib"
    fitted_model.save(path)
    loaded = BurnoutIsolationForest.load(path)
    np.testing.assert_array_equal(
        fitted_model.predict(X_test),
        loaded.predict(X_test),
    )


def test_save_creates_parent_dirs(fitted_model: BurnoutIsolationForest, tmp_path: Path) -> None:
    path = tmp_path / "nested" / "subdir" / "model.joblib"
    fitted_model.save(path)
    assert path.exists()
