"""Unit tests for ml.training.dataset — temporal split and AFS enrichment."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.training.dataset import DatasetSplit, add_afs_and_zone, temporal_split
from ml.training.features import AFS_COL, RAW_FEATURE_COLS, ZONE_COL
from ml.training.synthetic import SyntheticDataGenerator


@pytest.fixture(scope="module")
def synthetic_df() -> pd.DataFrame:
    return SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=20, n_days=60)


# ── add_afs_and_zone ──────────────────────────────────────────────────────────


def test_add_afs_and_zone_appends_columns() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=5)
    raw = df[RAW_FEATURE_COLS + ["team_id", "date_utc"]].copy()
    enriched = add_afs_and_zone(raw)
    assert AFS_COL in enriched.columns
    assert ZONE_COL in enriched.columns


def test_add_afs_and_zone_does_not_mutate_input() -> None:
    df = SyntheticDataGenerator(seed=1).generate_dataframe(n_teams=3, n_days=3)
    original_cols = list(df.columns)
    _ = add_afs_and_zone(df[RAW_FEATURE_COLS])
    assert list(df.columns) == original_cols


# ── temporal_split — validation ───────────────────────────────────────────────


def test_too_few_dates_raises() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=2)
    with pytest.raises(ValueError, match="at least 3"):
        temporal_split(df)


def test_invalid_ratio_raises() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=10)
    with pytest.raises(ValueError, match="must be < 1.0"):
        temporal_split(df, train_ratio=0.7, val_ratio=0.4)


def test_zero_ratio_raises() -> None:
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=5, n_days=10)
    with pytest.raises(ValueError):
        temporal_split(df, train_ratio=0.0, val_ratio=0.15)


# ── temporal_split — correctness ──────────────────────────────────────────────


def test_split_total_rows_equals_input(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    total = split.n_train + split.n_val + split.n_test
    assert total == len(synthetic_df)


def test_split_no_date_overlap(synthetic_df: pd.DataFrame) -> None:
    """Dates in train, val, test partitions must be mutually exclusive."""
    split = temporal_split(synthetic_df)

    dates = sorted(synthetic_df["date_utc"].unique())
    n = len(dates)
    # Infer partitions from boundary dates
    train_end_idx = dates.index(split.train_end_date)
    val_end_idx = dates.index(split.val_end_date)

    train_dates = set(dates[: train_end_idx + 1])
    val_dates = set(dates[train_end_idx + 1 : val_end_idx + 1])
    test_dates = set(dates[val_end_idx + 1 :])

    assert not train_dates & val_dates, "Train and val dates overlap"
    assert not val_dates & test_dates, "Val and test dates overlap"
    assert not train_dates & test_dates, "Train and test dates overlap"


def test_split_chronological_order(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    assert split.train_end_date < split.val_end_date < split.test_end_date


def test_split_train_is_largest(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    assert split.n_train > split.n_val
    assert split.n_train > split.n_test


def test_split_returns_float32_X(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    assert split.X_train.dtype == np.float32
    assert split.X_val.dtype == np.float32
    assert split.X_test.dtype == np.float32


def test_split_returns_int32_y(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    assert split.y_train.dtype == np.int32


def test_split_y_values_are_0_1_2(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    for y in (split.y_train, split.y_val, split.y_test):
        assert set(np.unique(y)).issubset({0, 1, 2})


def test_split_X_column_count_matches_feature_cols(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    assert split.X_train.shape[1] == len(RAW_FEATURE_COLS)


def test_split_summary_has_expected_keys(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df)
    summary = split.summary()
    assert set(summary.keys()) == {
        "n_train", "n_val", "n_test",
        "train_end_date", "val_end_date", "test_end_date",
    }


def test_split_custom_ratios(synthetic_df: pd.DataFrame) -> None:
    split = temporal_split(synthetic_df, train_ratio=0.60, val_ratio=0.20)
    total = split.n_train + split.n_val + split.n_test
    assert total == len(synthetic_df)
    # Train should be roughly 60 % — allow ±10 % for rounding on date boundaries
    assert split.n_train / total == pytest.approx(0.60, abs=0.10)
