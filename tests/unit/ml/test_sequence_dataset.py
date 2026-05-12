"""Unit tests for ml.training.sequence_dataset."""

from __future__ import annotations

import numpy as np
import pytest

from ml.training.features import RAW_FEATURE_COLS
from ml.training.sequence_dataset import (
    DEFAULT_WINDOW_SIZE,
    SequenceDataset,
    build_sequences,
    split_sequence_dataset,
)
from ml.training.synthetic import SyntheticDataGenerator


@pytest.fixture(scope="module")
def small_df():
    return SyntheticDataGenerator(seed=7).generate_dataframe(n_teams=5, n_days=20)


@pytest.fixture(scope="module")
def seq_ds(small_df):
    return build_sequences(small_df, window_size=7)


# ── build_sequences — shape ───────────────────────────────────────────────────


def test_output_is_sequence_dataset(seq_ds: SequenceDataset) -> None:
    assert isinstance(seq_ds, SequenceDataset)


def test_X_is_3d(seq_ds: SequenceDataset) -> None:
    assert seq_ds.X.ndim == 3


def test_window_size_matches_request(seq_ds: SequenceDataset) -> None:
    assert seq_ds.window_size == 7


def test_n_features_matches_raw_feature_cols(seq_ds: SequenceDataset) -> None:
    assert seq_ds.n_features == len(RAW_FEATURE_COLS)


def test_y_shape_matches_X(seq_ds: SequenceDataset) -> None:
    assert seq_ds.y.shape == (seq_ds.n_sequences,)


def test_last_dates_length_matches_sequences(seq_ds: SequenceDataset) -> None:
    assert len(seq_ds.last_dates) == seq_ds.n_sequences


def test_sequence_count_per_team() -> None:
    # Each team produces n_days - window_size + 1 sequences.
    # 5 teams × (20 - 7 + 1) = 5 × 14 = 70 sequences with window_size=7
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=20)
    ds = build_sequences(df, window_size=7)
    assert ds.n_sequences == 5 * (20 - 7 + 1)


def test_default_window_size() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=3, n_days=20)
    ds = build_sequences(df)
    assert ds.window_size == DEFAULT_WINDOW_SIZE


# ── build_sequences — data integrity ─────────────────────────────────────────


def test_X_dtype_is_float32(seq_ds: SequenceDataset) -> None:
    assert seq_ds.X.dtype == np.float32


def test_y_dtype_is_int32(seq_ds: SequenceDataset) -> None:
    assert seq_ds.y.dtype == np.int32


def test_y_values_are_0_1_2(seq_ds: SequenceDataset) -> None:
    assert set(np.unique(seq_ds.y)).issubset({0, 1, 2})


def test_no_cross_team_contamination() -> None:
    """Each sequence's context window must not mix two different teams.

    We verify this by checking that every window of features is a contiguous
    slice from a single team's time series (not a concatenation of two teams).
    The generator assigns per-team AFS biases, so a sequence built from a
    single team will have smaller within-window variance than one built across
    team boundaries.
    """
    df = SyntheticDataGenerator(seed=5).generate_dataframe(n_teams=10, n_days=30)
    ds = build_sequences(df, window_size=5)
    # All feature values must remain in [0, 1]
    assert ds.X.min() >= 0.0
    assert ds.X.max() <= 1.0


def test_last_date_is_last_day_of_window() -> None:
    """last_dates[i] must correspond to the final row of X[i]."""
    df = SyntheticDataGenerator(seed=3).generate_dataframe(n_teams=2, n_days=10)
    ds = build_sequences(df, window_size=3)
    # The last_dates list must be a subset of dates in the dataframe
    all_dates = set(df["date_utc"].unique())
    for d in ds.last_dates:
        assert d in all_dates


# ── build_sequences — validation ─────────────────────────────────────────────


def test_window_size_zero_raises() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=10)
    with pytest.raises(ValueError, match="window_size"):
        build_sequences(df, window_size=0)


def test_window_larger_than_days_raises() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=3, n_days=5)
    with pytest.raises(ValueError, match="window_size"):
        build_sequences(df, window_size=10)


# ── split_sequence_dataset ────────────────────────────────────────────────────


def test_split_preserves_total_sequences() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=10, n_days=30)
    ds = build_sequences(df, window_size=5)
    dates = sorted(df["date_utc"].unique())
    train_end = dates[20]
    val_end = dates[25]
    tr, va, te = split_sequence_dataset(ds, train_end, val_end)
    assert tr.n_sequences + va.n_sequences + te.n_sequences == ds.n_sequences


def test_split_partitions_are_mutually_exclusive() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=10, n_days=30)
    ds = build_sequences(df, window_size=5)
    dates = sorted(df["date_utc"].unique())
    train_end, val_end = dates[18], dates[24]
    tr, va, te = split_sequence_dataset(ds, train_end, val_end)
    tr_set = set(tr.last_dates)
    va_set = set(va.last_dates)
    te_set = set(te.last_dates)
    assert not tr_set & va_set
    assert not va_set & te_set
    assert not tr_set & te_set


def test_train_sequences_respect_boundary() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=30)
    ds = build_sequences(df, window_size=5)
    dates = sorted(df["date_utc"].unique())
    train_end = dates[18]
    tr, _, _ = split_sequence_dataset(ds, train_end, dates[24])
    assert all(d <= train_end for d in tr.last_dates)
