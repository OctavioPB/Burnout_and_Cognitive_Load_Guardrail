"""Unit tests for ml.training.ensemble — EnsembleScorer and _afs_soft_proba."""

from __future__ import annotations

import numpy as np
import pytest

from ml.training.dataset import temporal_split
from ml.training.ensemble import EnsembleScorer, _afs_soft_proba
from ml.training.isolation_forest import BurnoutIsolationForest
from ml.training.lstm_model import LSTMTrainer
from ml.training.sequence_dataset import build_sequences, split_sequence_dataset
from ml.training.synthetic import SyntheticDataGenerator


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def fitted_ensemble():
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=15, n_days=25)
    split = temporal_split(df)
    seq_ds = build_sequences(df, window_size=5)
    seq_tr, seq_va, seq_te = split_sequence_dataset(
        seq_ds, split.train_end_date, split.val_end_date
    )

    if_model = BurnoutIsolationForest()
    if_model.fit(split.X_train)

    lstm = LSTMTrainer(hidden_size=8, num_layers=1, max_epochs=3, patience=3, device="cpu")
    if seq_tr.n_sequences > 0 and seq_va.n_sequences > 0:
        lstm.fit(seq_tr.X, seq_tr.y, seq_va.X, seq_va.y)

    return EnsembleScorer(if_model, lstm), seq_te


# ── _afs_soft_proba ───────────────────────────────────────────────────────────


def test_afs_zero_mostly_green() -> None:
    proba = _afs_soft_proba(np.array([0.0]))
    assert proba[0, 0] > 0.7, f"P(green) at AFS=0 should be >0.7, got {proba[0, 0]:.3f}"


def test_afs_100_mostly_red() -> None:
    proba = _afs_soft_proba(np.array([100.0]))
    assert proba[0, 2] > 0.7, f"P(red) at AFS=100 should be >0.7, got {proba[0, 2]:.3f}"


def test_afs_soft_proba_sums_to_one() -> None:
    afs = np.linspace(0, 100, 50)
    proba = _afs_soft_proba(afs)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_afs_soft_proba_all_non_negative() -> None:
    proba = _afs_soft_proba(np.linspace(0, 100, 100))
    assert (proba >= 0.0).all()


def test_afs_soft_proba_shape() -> None:
    proba = _afs_soft_proba(np.array([10.0, 50.0, 90.0]))
    assert proba.shape == (3, 3)


def test_afs_increases_red_probability() -> None:
    """Higher AFS should give monotonically increasing P(red)."""
    afs_values = np.array([10.0, 40.0, 70.0, 100.0])
    proba = _afs_soft_proba(afs_values)
    # P(red) should increase as AFS increases
    p_red = proba[:, 2]
    assert (np.diff(p_red) > 0).all(), f"P(red) not monotone: {p_red}"


# ── EnsembleScorer construction ───────────────────────────────────────────────


def test_invalid_weights_raise() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=10)
    split = temporal_split(df)
    if_model = BurnoutIsolationForest()
    if_model.fit(split.X_train)
    lstm = LSTMTrainer(device="cpu")
    with pytest.raises(ValueError, match="sum to 1.0"):
        EnsembleScorer(if_model, lstm, if_weight=0.5, lstm_weight=0.5, afs_weight=0.5)


# ── predict_proba ─────────────────────────────────────────────────────────────


def test_predict_proba_shape(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    proba = scorer.predict_proba(seq_te.X)
    assert proba.shape == (seq_te.n_sequences, 3)


def test_predict_proba_sums_to_one(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    proba = scorer.predict_proba(seq_te.X)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_predict_proba_all_non_negative(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    proba = scorer.predict_proba(seq_te.X)
    assert (proba >= 0.0).all()


def test_predict_proba_dtype(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    proba = scorer.predict_proba(seq_te.X)
    assert proba.dtype == np.float32


# ── predict ───────────────────────────────────────────────────────────────────


def test_predict_values_in_valid_range(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    y = scorer.predict(seq_te.X)
    assert set(np.unique(y)).issubset({0, 1, 2})


def test_predict_dtype(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    y = scorer.predict(seq_te.X)
    assert y.dtype == np.int32


def test_predict_shape(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    y = scorer.predict(seq_te.X)
    assert y.shape == (seq_te.n_sequences,)


def test_predict_consistent_with_predict_proba(fitted_ensemble) -> None:
    scorer, seq_te = fitted_ensemble
    if seq_te.n_sequences == 0:
        pytest.skip("No test sequences")
    proba = scorer.predict_proba(seq_te.X)
    y_from_proba = proba.argmax(axis=1).astype(np.int32)
    y_direct = scorer.predict(seq_te.X)
    np.testing.assert_array_equal(y_direct, y_from_proba)
