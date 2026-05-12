"""Unit tests for ml.training.lstm_model — BurnoutLSTM and LSTMTrainer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from ml.training.dataset import temporal_split
from ml.training.lstm_model import BurnoutLSTM, LSTMTrainer, TrainResult
from ml.training.sequence_dataset import build_sequences, split_sequence_dataset
from ml.training.synthetic import SyntheticDataGenerator

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tiny_sequences():
    """Minimal sequences for fast training tests (window=3, 2-epoch cap)."""
    df = SyntheticDataGenerator(seed=11).generate_dataframe(n_teams=10, n_days=20)
    ds = build_sequences(df, window_size=3)
    split = temporal_split(df)
    tr, va, te = split_sequence_dataset(ds, split.train_end_date, split.val_end_date)
    return tr, va, te


@pytest.fixture(scope="module")
def fitted_trainer(tiny_sequences) -> LSTMTrainer:
    tr, va, _ = tiny_sequences
    trainer = LSTMTrainer(hidden_size=8, num_layers=1, max_epochs=3, patience=3, device="cpu")
    trainer.fit(tr.X, tr.y, va.X, va.y)
    return trainer


# ── BurnoutLSTM ───────────────────────────────────────────────────────────────


def test_lstm_forward_output_shape() -> None:
    model = BurnoutLSTM(input_size=4, hidden_size=16, num_layers=1)
    x = torch.randn(8, 7, 4)  # (batch=8, seq=7, features=4)
    out = model(x)
    assert out.shape == (8, 3)


def test_lstm_forward_different_batch_sizes() -> None:
    model = BurnoutLSTM(input_size=4, hidden_size=16, num_layers=1)
    for batch in (1, 4, 32):
        out = model(torch.randn(batch, 5, 4))
        assert out.shape == (batch, 3)


def test_lstm_output_is_logits_not_proba() -> None:
    """Forward pass returns raw logits — they should NOT sum to ~1 per row."""
    model = BurnoutLSTM(input_size=4, hidden_size=16, num_layers=1)
    x = torch.randn(4, 5, 4)
    logits = model(x)
    row_sums = logits.sum(dim=1).detach().numpy()
    # Logits do not sum to 1; if they did, model is returning probabilities (bug)
    assert not np.allclose(np.abs(row_sums), 1.0, atol=0.1)


# ── LSTMTrainer.fit ───────────────────────────────────────────────────────────


def test_fit_returns_train_result(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    tr, va, _ = tiny_sequences
    result = LSTMTrainer(hidden_size=8, num_layers=1, max_epochs=2, patience=2, device="cpu").fit(
        tr.X, tr.y, va.X, va.y
    )
    assert isinstance(result, TrainResult)


def test_fit_sets_model(fitted_trainer: LSTMTrainer) -> None:
    assert fitted_trainer.model is not None


def test_fit_train_losses_non_empty(tiny_sequences) -> None:
    tr, va, _ = tiny_sequences
    trainer = LSTMTrainer(hidden_size=8, num_layers=1, max_epochs=3, patience=5, device="cpu")
    result = trainer.fit(tr.X, tr.y, va.X, va.y)
    assert len(result.train_losses) > 0


def test_fit_best_epoch_within_range(tiny_sequences) -> None:
    tr, va, _ = tiny_sequences
    trainer = LSTMTrainer(hidden_size=8, num_layers=1, max_epochs=5, patience=5, device="cpu")
    result = trainer.fit(tr.X, tr.y, va.X, va.y)
    assert 0 <= result.best_epoch < 5


def test_fit_raises_on_non_3d_input(tiny_sequences) -> None:
    tr, va, _ = tiny_sequences
    trainer = LSTMTrainer(device="cpu")
    with pytest.raises(ValueError, match="3-D"):
        trainer.fit(tr.X[:, 0, :], tr.y, va.X, va.y)  # 2-D input


# ── LSTMTrainer.predict_proba ─────────────────────────────────────────────────


def test_predict_proba_shape(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    proba = fitted_trainer.predict_proba(te.X)
    assert proba.shape == (te.n_sequences, 3)


def test_predict_proba_sums_to_one(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    proba = fitted_trainer.predict_proba(te.X)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_predict_proba_all_non_negative(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    proba = fitted_trainer.predict_proba(te.X)
    assert (proba >= 0.0).all()


def test_predict_proba_dtype(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    proba = fitted_trainer.predict_proba(te.X)
    assert proba.dtype == np.float32


def test_predict_before_fit_raises() -> None:
    trainer = LSTMTrainer(device="cpu")
    X = np.zeros((5, 7, 4), dtype=np.float32)
    with pytest.raises(RuntimeError, match="fit"):
        trainer.predict(X)


# ── LSTMTrainer.predict ───────────────────────────────────────────────────────


def test_predict_values_in_valid_range(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    y = fitted_trainer.predict(te.X)
    assert set(np.unique(y)).issubset({0, 1, 2})


def test_predict_dtype(fitted_trainer: LSTMTrainer, tiny_sequences) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    y = fitted_trainer.predict(te.X)
    assert y.dtype == np.int32


# ── Serialization ─────────────────────────────────────────────────────────────


def test_save_load_round_trip(fitted_trainer: LSTMTrainer, tiny_sequences, tmp_path: Path) -> None:
    _, _, te = tiny_sequences
    if te.n_sequences == 0:
        pytest.skip("No test sequences for this split")
    path = tmp_path / "lstm.pt"
    fitted_trainer.save(path)
    loaded = LSTMTrainer.load(path)
    np.testing.assert_array_equal(
        fitted_trainer.predict(te.X),
        loaded.predict(te.X),
    )


def test_save_creates_parent_dirs(fitted_trainer: LSTMTrainer, tmp_path: Path) -> None:
    path = tmp_path / "nested" / "subdir" / "model.pt"
    fitted_trainer.save(path)
    assert path.exists()


def test_save_before_fit_raises(tmp_path: Path) -> None:
    trainer = LSTMTrainer(device="cpu")
    with pytest.raises(RuntimeError, match="fit"):
        trainer.save(tmp_path / "model.pt")
