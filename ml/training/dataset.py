"""Temporal train / validation / test split for the feature dataset.

Key design constraint: **no data leakage across time**.
The dataset is sorted by date and split chronologically so that the model
always trains on past data and evaluates on future data.  Random splits
are explicitly forbidden here — they would leak future burnout states into
training (a team's status on day N+1 is correlated with day N).

Split ratios (default):
  Train : 0.70  (earliest 70 % of dates)
  Val   : 0.15  (next 15 %)
  Test  : 0.15  (latest 15 %)

The unit of splitting is the **calendar date**, not the row index, so all
team records for a given date land in the same partition.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.training.features import AFS_COL, RAW_FEATURE_COLS, ZONE_COL

_DEFAULT_TRAIN_RATIO: float = 0.70
_DEFAULT_VAL_RATIO: float = 0.15
# test_ratio = 1.0 - train - val


@dataclass(frozen=True)
class DatasetSplit:
    """Holds feature matrices and labels for all three partitions."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray

    # Date boundaries for reproducibility logging
    train_end_date: str
    val_end_date: str
    test_end_date: str

    @property
    def n_train(self) -> int:
        return int(self.X_train.shape[0])

    @property
    def n_val(self) -> int:
        return int(self.X_val.shape[0])

    @property
    def n_test(self) -> int:
        return int(self.X_test.shape[0])

    def summary(self) -> dict[str, object]:
        return {
            "n_train": self.n_train,
            "n_val": self.n_val,
            "n_test": self.n_test,
            "train_end_date": self.train_end_date,
            "val_end_date": self.val_end_date,
            "test_end_date": self.test_end_date,
        }


def temporal_split(
    df: pd.DataFrame,
    train_ratio: float = _DEFAULT_TRAIN_RATIO,
    val_ratio: float = _DEFAULT_VAL_RATIO,
    date_col: str = "date_utc",
    feature_cols: list[str] | None = None,
    label_col: str = ZONE_COL,
) -> DatasetSplit:
    """Split a feature DataFrame into train / val / test by date order.

    Args:
        df: DataFrame containing feature columns, a date column, and a label
            column.  Must have at least 3 distinct dates.
        train_ratio: Fraction of unique dates assigned to training.
        val_ratio: Fraction of unique dates assigned to validation.
                   Remainder goes to test.
        date_col: Name of the date column used for ordering.
        feature_cols: Columns to include in X arrays.  Defaults to RAW_FEATURE_COLS.
        label_col: Column containing integer or string labels.

    Returns:
        DatasetSplit with numpy arrays for X and y in each partition.

    Raises:
        ValueError: If df has fewer than 3 distinct dates, or ratios are invalid.
    """
    if feature_cols is None:
        feature_cols = RAW_FEATURE_COLS

    if train_ratio + val_ratio >= 1.0:
        raise ValueError(
            f"train_ratio ({train_ratio}) + val_ratio ({val_ratio}) must be < 1.0"
        )
    if train_ratio <= 0 or val_ratio <= 0:
        raise ValueError("train_ratio and val_ratio must both be positive")

    sorted_dates = sorted(df[date_col].unique())
    n_dates = len(sorted_dates)
    if n_dates < 3:
        raise ValueError(
            f"Dataset must span at least 3 distinct dates; found {n_dates}"
        )

    train_cutoff_idx = max(1, int(n_dates * train_ratio))
    val_cutoff_idx = max(train_cutoff_idx + 1, int(n_dates * (train_ratio + val_ratio)))
    val_cutoff_idx = min(val_cutoff_idx, n_dates - 1)

    train_dates = set(sorted_dates[:train_cutoff_idx])
    val_dates = set(sorted_dates[train_cutoff_idx:val_cutoff_idx])
    test_dates = set(sorted_dates[val_cutoff_idx:])

    train_df = df[df[date_col].isin(train_dates)]
    val_df = df[df[date_col].isin(val_dates)]
    test_df = df[df[date_col].isin(test_dates)]

    def _to_arrays(part: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        X = part[feature_cols].fillna(0.0).to_numpy(dtype=np.float32)
        if pd.api.types.is_integer_dtype(part[label_col]):
            y = part[label_col].to_numpy(dtype=np.int32)
        else:
            # String zone labels → integer encoding via sorted order
            label_map = {"green": 0, "yellow": 1, "red": 2}
            y = part[label_col].map(label_map).to_numpy(dtype=np.int32)
        return X, y

    X_train, y_train = _to_arrays(train_df)
    X_val, y_val = _to_arrays(val_df)
    X_test, y_test = _to_arrays(test_df)

    return DatasetSplit(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        X_test=X_test,
        y_test=y_test,
        train_end_date=str(sorted_dates[train_cutoff_idx - 1]),
        val_end_date=str(sorted_dates[val_cutoff_idx - 1]),
        test_end_date=str(sorted_dates[-1]),
    )


def add_afs_and_zone(df: pd.DataFrame) -> pd.DataFrame:
    """Compute AFS and resilience_zone columns from raw feature columns.

    Mutates nothing; returns a new DataFrame with two extra columns appended.

    Args:
        df: DataFrame containing all RAW_FEATURE_COLS.

    Returns:
        New DataFrame with ``afs`` and ``resilience_zone`` columns added.
    """
    from ml.training.features import afs_to_zone, compute_afs_from_row

    out = df.copy()
    out[AFS_COL] = out.apply(compute_afs_from_row, axis=1)
    out[ZONE_COL] = out[AFS_COL].apply(lambda v: afs_to_zone(v).value)
    return out
