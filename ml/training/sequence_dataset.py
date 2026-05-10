"""Rolling-window sequence builder for LSTM training.

Each sequence is a window of ``window_size`` consecutive team-days, labeled by
the ResilienceZone of the **last** day in the window.  Sequences are built
per-team to prevent stitching different teams' temporal signals together.

Temporal split note
-------------------
``build_sequences`` operates on the *full* DataFrame; the resulting
``SequenceDataset`` is then partitioned by ``split_sequence_dataset`` so that
a sequence belongs to the partition of its last date.  This means a validation
or test sequence may have context days that fall inside the training window —
which is correct and expected (no label leakage because only the last day's
label is used as target).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.training.features import RAW_FEATURE_COLS, ZONE_COL

DEFAULT_WINDOW_SIZE: int = 14

_LABEL_MAP: dict[str, int] = {"green": 0, "yellow": 1, "red": 2}


@dataclass(frozen=True)
class SequenceDataset:
    """Rolling-window sequences ready for LSTM training/evaluation.

    Attributes:
        X: Float32 array of shape (n_sequences, window_size, n_features).
        y: Int32 label array of shape (n_sequences,) — label of the last day.
        last_dates: ISO date string for the last day in each sequence.
    """

    X: np.ndarray
    y: np.ndarray
    last_dates: list[str]

    @property
    def n_sequences(self) -> int:
        return int(self.X.shape[0])

    @property
    def window_size(self) -> int:
        return int(self.X.shape[1])

    @property
    def n_features(self) -> int:
        return int(self.X.shape[2])


def build_sequences(
    df: pd.DataFrame,
    window_size: int = DEFAULT_WINDOW_SIZE,
    feature_cols: list[str] | None = None,
    label_col: str = ZONE_COL,
    team_col: str = "team_id",
    date_col: str = "date_utc",
) -> SequenceDataset:
    """Build per-team rolling windows from a feature DataFrame.

    Args:
        df: Feature DataFrame containing team_id, date_utc, feature cols,
            and a zone label column.
        window_size: Number of consecutive days per sequence (>= 1).
        feature_cols: Columns to use as features.  Defaults to RAW_FEATURE_COLS.
        label_col: Column with ResilienceZone string or integer labels.
        team_col: Column identifying the team.
        date_col: Column identifying the date (used only for sorting and
                  recording ``last_dates``; no assumption of date arithmetic).

    Returns:
        SequenceDataset with X of shape (n_sequences, window_size, n_features).

    Raises:
        ValueError: If window_size < 1 or no sequences can be built.
    """
    if window_size < 1:
        raise ValueError(f"window_size must be >= 1; got {window_size}")

    if feature_cols is None:
        feature_cols = RAW_FEATURE_COLS

    all_X: list[np.ndarray] = []
    all_y: list[int] = []
    all_dates: list[str] = []

    for _team_id, team_df in df.groupby(team_col):
        team_df = team_df.sort_values(date_col)
        feat = team_df[feature_cols].fillna(0.0).to_numpy(dtype=np.float32)
        dates = team_df[date_col].tolist()

        if pd.api.types.is_integer_dtype(team_df[label_col]):
            labels = team_df[label_col].to_numpy(dtype=np.int32)
        else:
            labels = np.array(
                [_LABEL_MAP.get(str(z), 0) for z in team_df[label_col]],
                dtype=np.int32,
            )

        n = len(feat)
        for i in range(window_size, n + 1):
            all_X.append(feat[i - window_size : i])
            all_y.append(int(labels[i - 1]))
            all_dates.append(str(dates[i - 1]))

    if not all_X:
        raise ValueError(
            f"No sequences could be built with window_size={window_size}. "
            "Reduce window_size or use a larger dataset."
        )

    return SequenceDataset(
        X=np.stack(all_X, axis=0),
        y=np.array(all_y, dtype=np.int32),
        last_dates=all_dates,
    )


def split_sequence_dataset(
    seq_ds: SequenceDataset,
    train_end_date: str,
    val_end_date: str,
) -> tuple[SequenceDataset, SequenceDataset, SequenceDataset]:
    """Partition a SequenceDataset by each sequence's last date.

    A sequence belongs to:
      - **train** if ``last_date <= train_end_date``
      - **val**   if ``train_end_date < last_date <= val_end_date``
      - **test**  if ``last_date > val_end_date``

    Args:
        seq_ds: Full SequenceDataset built from all dates.
        train_end_date: Inclusive boundary for the training partition.
        val_end_date: Inclusive boundary for the validation partition.

    Returns:
        (train_seq_ds, val_seq_ds, test_seq_ds) — each a SequenceDataset.
    """
    last_dates = np.array(seq_ds.last_dates)
    train_mask = last_dates <= train_end_date
    val_mask = (last_dates > train_end_date) & (last_dates <= val_end_date)
    test_mask = last_dates > val_end_date

    def _subset(mask: np.ndarray) -> SequenceDataset:
        idx = np.where(mask)[0]
        return SequenceDataset(
            X=seq_ds.X[idx],
            y=seq_ds.y[idx],
            last_dates=[seq_ds.last_dates[i] for i in idx.tolist()],
        )

    return _subset(train_mask), _subset(val_mask), _subset(test_mask)
