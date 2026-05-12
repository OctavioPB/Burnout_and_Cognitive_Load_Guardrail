"""Ensemble scorer combining Isolation Forest, LSTM, and AFS-based signals.

Three components, each producing P(Green, Yellow, Red):

1. **BurnoutIsolationForest (30%)** — point-in-time feature anomaly detection.
   Receives the last timestep of each sequence (``X_seq[:, -1, :]``).

2. **LSTMTrainer (40%)** — 14-day trend classifier.
   Receives the full sequence tensor ``X_seq``.

3. **AFS soft probabilities (30%)** — domain knowledge prior via sigmoid
   functions centered on the Green/Yellow/Red zone thresholds (40 and 70).
   AFS is computed on-the-fly from the last timestep features.

The final prediction is the argmax of the weighted average probability vector.

Cold-start note
---------------
Teams with < 14 days of data cannot produce a valid sequence.  In that case,
use ``BurnoutIsolationForest.predict`` or the AFS hard thresholds directly.
This fallback is handled in ``ml.inference`` (Sprint 6), not here.
"""

from __future__ import annotations

import logging

import numpy as np

from ml.training.features import RAW_FEATURE_COLS, compute_afs_from_row
from ml.training.isolation_forest import BurnoutIsolationForest
from ml.training.lstm_model import LSTMTrainer

logger = logging.getLogger(__name__)

# Default component weights — must sum to 1.0
_IF_WEIGHT: float = 0.30
_LSTM_WEIGHT: float = 0.40
_AFS_WEIGHT: float = 0.30

assert abs(_IF_WEIGHT + _LSTM_WEIGHT + _AFS_WEIGHT - 1.0) < 1e-9

# Sigmoid sharpness for the AFS → soft-probability mapping.
# Smaller k = smoother transition at zone boundaries.
_SIGMOID_K: float = 0.20


def _afs_soft_proba(afs_scores: np.ndarray) -> np.ndarray:
    """Map AFS values [0, 100] to soft class probabilities via sigmoid boundaries.

    Uses sigmoid functions centered on the zone thresholds (40 = Green→Yellow,
    70 = Yellow→Red) to produce a smooth, differentiable probability distribution.

    Args:
        afs_scores: 1D float array of AFS values in [0, 100].

    Returns:
        Float32 array of shape (n_samples, 3) — [P(green), P(yellow), P(red)].
    """
    k = _SIGMOID_K

    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-k * x))

    p_not_green = _sigmoid(afs_scores - 40.0)   # cumulative: P(yellow or red)
    p_red = _sigmoid(afs_scores - 70.0)          # cumulative: P(red)
    p_green = 1.0 - p_not_green
    p_yellow = np.clip(p_not_green - p_red, 0.0, 1.0)

    raw = np.stack([p_green, p_yellow, p_red], axis=1).astype(np.float64)
    row_sums = raw.sum(axis=1, keepdims=True)
    return (raw / row_sums).astype(np.float32)  # type: ignore[no-any-return]


class EnsembleScorer:
    """Weighted-average ensemble of IF, LSTM, and AFS-based probabilities.

    Args:
        if_model: Fitted BurnoutIsolationForest.
        lstm_trainer: Fitted LSTMTrainer.
        if_weight: Weight for IF component (default 0.30).
        lstm_weight: Weight for LSTM component (default 0.40).
        afs_weight: Weight for AFS component (default 0.30).
    """

    def __init__(
        self,
        if_model: BurnoutIsolationForest,
        lstm_trainer: LSTMTrainer,
        if_weight: float = _IF_WEIGHT,
        lstm_weight: float = _LSTM_WEIGHT,
        afs_weight: float = _AFS_WEIGHT,
    ) -> None:
        if abs(if_weight + lstm_weight + afs_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Ensemble weights must sum to 1.0; got {if_weight + lstm_weight + afs_weight:.6f}"
            )
        self._if = if_model
        self._lstm = lstm_trainer
        self._if_weight = if_weight
        self._lstm_weight = lstm_weight
        self._afs_weight = afs_weight

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_proba(self, X_seq: np.ndarray) -> np.ndarray:
        """Compute weighted-average class probabilities.

        Args:
            X_seq: Float32 array of shape (n, window_size, n_features).
                   The last timestep (``X_seq[:, -1, :]``) is used as the
                   point-in-time input for the IF and AFS components.

        Returns:
            Float32 array of shape (n, 3) — [P(green), P(yellow), P(red)].
        """
        X_last = X_seq[:, -1, :]  # (n, n_features) — current day's features

        # Compute AFS from last-timestep features
        afs_scores = np.array(
            [
                compute_afs_from_row(dict(zip(RAW_FEATURE_COLS, row.tolist(), strict=False)))
                for row in X_last
            ],
            dtype=np.float32,
        )

        p_if = self._if.predict_proba(X_last)       # (n, 3)
        p_lstm = self._lstm.predict_proba(X_seq)     # (n, 3)
        p_afs = _afs_soft_proba(afs_scores)          # (n, 3)

        ensemble = (
            self._if_weight * p_if
            + self._lstm_weight * p_lstm
            + self._afs_weight * p_afs
        )
        return ensemble.astype(np.float32)

    def predict(self, X_seq: np.ndarray) -> np.ndarray:
        """Return integer class predictions (0=green, 1=yellow, 2=red).

        Args:
            X_seq: Float32 array of shape (n, window_size, n_features).

        Returns:
            Int32 array of shape (n,).
        """
        return self.predict_proba(X_seq).argmax(axis=1).astype(np.int32)  # type: ignore[no-any-return]
