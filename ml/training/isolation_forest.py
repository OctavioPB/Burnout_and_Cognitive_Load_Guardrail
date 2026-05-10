"""Isolation Forest anomaly detector for point-in-time burnout risk.

The IF operates on the raw 4-feature vector (calendar density, after-hours
activity, context switches, sprint health) without temporal context.  It
captures unusual *combinations* of features — e.g. simultaneously high context
switches AND calendar density — that the AFS weighted sum can obscure by
averaging.

Score calibration
-----------------
sklearn's ``decision_function`` returns higher values for *normal* observations.
We invert it (multiply by −1) so that higher values mean more anomalous, then
scale to [0, 1] via a MinMaxScaler fitted on the training data.  This scaled
anomaly score feeds into the EnsembleScorer as the IF component's signal.

Three-class heuristic
---------------------
The IF natively produces a binary signal (anomaly vs. normal).  To participate
in the three-class ensemble we map the anomaly score to soft probabilities:
  - P(Red)    ∝ score            (high anomaly → Red)
  - P(Yellow) ∝ 4 × score × (1−score)   (peaks at score = 0.5, uncertain territory)
  - P(Green)  ∝ (1 − score)     (low anomaly → Green)
Rows are L1-normalized so probabilities sum to 1.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

_DEFAULT_CONTAMINATION: float = 0.15   # matches ~Red zone proportion
_DEFAULT_N_ESTIMATORS: int = 100
_DEFAULT_RANDOM_STATE: int = 42


class BurnoutIsolationForest:
    """sklearn IsolationForest wrapper calibrated for burnout risk scoring.

    Args:
        contamination: Expected anomaly fraction (roughly the Red zone rate).
        n_estimators: Number of isolation trees.
        random_state: Seed for reproducibility.
    """

    def __init__(
        self,
        contamination: float = _DEFAULT_CONTAMINATION,
        n_estimators: int = _DEFAULT_N_ESTIMATORS,
        random_state: int = _DEFAULT_RANDOM_STATE,
    ) -> None:
        self._if = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self._scaler = MinMaxScaler()
        self._is_fitted: bool = False

    # ── Fit ───────────────────────────────────────────────────────────────────

    def fit(self, X: np.ndarray) -> "BurnoutIsolationForest":
        """Train the forest and fit the anomaly score scaler.

        Args:
            X: Float array of shape (n_samples, n_features).

        Returns:
            self — for method chaining.
        """
        self._if.fit(X)
        raw_scores = self._if.decision_function(X)
        # Invert: sklearn scores higher = more normal; we want higher = more anomalous
        inverted = (-raw_scores).reshape(-1, 1)
        self._scaler.fit(inverted)
        self._is_fitted = True
        logger.info(
            "IsolationForest fitted: n_samples=%d  n_features=%d",
            X.shape[0],
            X.shape[1],
        )
        return self

    # ── Scoring ───────────────────────────────────────────────────────────────

    def anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """Return a [0, 1] anomaly score per sample (higher = more anomalous).

        Args:
            X: Float array of shape (n_samples, n_features).

        Returns:
            Float32 array of shape (n_samples,).
        """
        self._check_fitted()
        raw = self._if.decision_function(X)
        scaled = self._scaler.transform((-raw).reshape(-1, 1)).ravel()
        return np.clip(scaled, 0.0, 1.0).astype(np.float32)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return soft class probabilities derived from the anomaly score.

        Args:
            X: Float array of shape (n_samples, n_features).

        Returns:
            Float32 array of shape (n_samples, 3) — [P(green), P(yellow), P(red)].
        """
        scores = self.anomaly_score(X)
        p_red = scores
        p_yellow = 4.0 * scores * (1.0 - scores)  # peaks at score=0.5
        p_green = 1.0 - scores

        raw = np.stack([p_green, p_yellow, p_red], axis=1).astype(np.float64)
        row_sums = raw.sum(axis=1, keepdims=True)
        return (raw / row_sums).astype(np.float32)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return integer class predictions (0=green, 1=yellow, 2=red).

        Args:
            X: Float array of shape (n_samples, n_features).

        Returns:
            Int32 array of shape (n_samples,).
        """
        return self.predict_proba(X).argmax(axis=1).astype(np.int32)

    # ── Serialization ─────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """Serialize model + scaler to a single joblib file.

        Args:
            path: Destination file path (parent dirs created if needed).
        """
        self._check_fitted()
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"if": self._if, "scaler": self._scaler}, path)
        logger.info("IsolationForest saved to %s", path)

    @classmethod
    def load(cls, path: Path) -> "BurnoutIsolationForest":
        """Load a previously saved BurnoutIsolationForest.

        Args:
            path: File produced by :meth:`save`.

        Returns:
            Loaded, fitted instance ready for inference.
        """
        data = joblib.load(path)
        obj = cls.__new__(cls)
        obj._if = data["if"]
        obj._scaler = data["scaler"]
        obj._is_fitted = True
        return obj

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError(
                "BurnoutIsolationForest must be fitted before calling predict methods."
            )
