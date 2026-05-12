"""Unit tests for ml.training.synthetic — SyntheticDataGenerator."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ml.training.features import AFS_COL, RAW_FEATURE_COLS, ZONE_COL, ResilienceZone
from ml.training.synthetic import SyntheticDataGenerator

# ── Constructor validation ────────────────────────────────────────────────────


def test_invalid_zone_weights_raise() -> None:
    with pytest.raises(ValueError, match=r"sum to 1\.0"):
        SyntheticDataGenerator(
            zone_weights={
                ResilienceZone.GREEN: 0.5,
                ResilienceZone.YELLOW: 0.3,
                ResilienceZone.RED: 0.5,  # sum = 1.3
            }
        )


# ── Reproducibility ───────────────────────────────────────────────────────────


def test_same_seed_produces_identical_dataframes() -> None:
    df1 = SyntheticDataGenerator(seed=99).generate_dataframe(n_teams=5, n_days=7)
    df2 = SyntheticDataGenerator(seed=99).generate_dataframe(n_teams=5, n_days=7)
    pd.testing.assert_frame_equal(df1, df2)


def test_different_seeds_produce_different_data() -> None:
    df1 = SyntheticDataGenerator(seed=1).generate_dataframe(n_teams=10, n_days=10)
    df2 = SyntheticDataGenerator(seed=2).generate_dataframe(n_teams=10, n_days=10)
    assert not df1[AFS_COL].equals(df2[AFS_COL])


# ── Output shape and schema ───────────────────────────────────────────────────


def test_dataframe_shape() -> None:
    n_teams, n_days = 10, 30
    df = SyntheticDataGenerator().generate_dataframe(n_teams=n_teams, n_days=n_days)
    assert df.shape == (n_teams * n_days, 9)


def test_dataframe_contains_required_columns() -> None:
    df = SyntheticDataGenerator().generate_dataframe()
    expected = {"team_id", "workspace_id", "date_utc"} | set(RAW_FEATURE_COLS) | {AFS_COL, ZONE_COL}
    assert expected.issubset(set(df.columns))


def test_n_distinct_teams_matches_request() -> None:
    df = SyntheticDataGenerator().generate_dataframe(n_teams=15, n_days=5)
    assert df["team_id"].nunique() == 15


def test_n_distinct_dates_matches_request() -> None:
    df = SyntheticDataGenerator().generate_dataframe(n_teams=3, n_days=20)
    assert df["date_utc"].nunique() == 20


# ── Feature value ranges ──────────────────────────────────────────────────────


def test_raw_features_within_zero_one() -> None:
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=20, n_days=30)
    for col in RAW_FEATURE_COLS:
        assert df[col].min() >= 0.0, f"{col} has value below 0"
        assert df[col].max() <= 1.0, f"{col} has value above 1"


def test_afs_within_zero_hundred() -> None:
    df = SyntheticDataGenerator(seed=42).generate_dataframe(n_teams=20, n_days=30)
    assert df[AFS_COL].min() >= 0.0
    assert df[AFS_COL].max() <= 100.0


def test_zone_values_are_valid() -> None:
    df = SyntheticDataGenerator().generate_dataframe()
    valid_zones = {z.value for z in ResilienceZone}
    assert set(df[ZONE_COL].unique()).issubset(valid_zones)


# ── Zone distribution ─────────────────────────────────────────────────────────


def test_zone_distribution_roughly_matches_weights() -> None:
    # Per-team zone bias (80% stability) means large n_days is needed for convergence.
    # With 100 teams, seed-dependent initial zone draws add ±15% variance.
    df = SyntheticDataGenerator(seed=0).generate_dataframe(n_teams=100, n_days=60)
    counts = df[ZONE_COL].value_counts(normalize=True)
    assert counts.get("green", 0) == pytest.approx(0.55, abs=0.15)
    assert counts.get("yellow", 0) == pytest.approx(0.30, abs=0.15)
    assert counts.get("red", 0) == pytest.approx(0.15, abs=0.15)


# ── Custom start date ─────────────────────────────────────────────────────────


def test_custom_start_date_is_respected() -> None:
    start = date(2024, 1, 1)
    df = SyntheticDataGenerator().generate_dataframe(n_teams=2, n_days=5, start_date=start)
    assert df["date_utc"].min() == "2024-01-01"
    assert df["date_utc"].max() == "2024-01-05"


# ── No NaN values ─────────────────────────────────────────────────────────────


def test_no_null_values_in_dataframe() -> None:
    df = SyntheticDataGenerator().generate_dataframe()
    assert df.isnull().sum().sum() == 0
