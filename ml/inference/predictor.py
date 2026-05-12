"""Core prediction logic for the inference service.

Two execution paths:

**Warm start** (history with ≥ 13 prior days provided)
    Uses the full EnsembleScorer (IF 30% + LSTM 40% + AFS 30%).

**Cold start** (no history, or fewer than 13 prior days)
    Uses IF + AFS only (50/50), with a ``cold_start=True`` flag in the response.
    Falls back to AFS-only if IF is also unavailable.

The predictor is a stateless function object — it holds no mutable state across
calls.  Alert tracking (consecutive Red days) is handled separately in
:mod:`ml.inference.alert_engine`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from ml.inference.config import (
    COLD_START_AFS_WEIGHT,
    COLD_START_IF_WEIGHT,
    LSTM_WINDOW_SIZE,
    MODEL_VERSION,
)
from ml.inference.model_loader import ModelBundle
from ml.training.ensemble import _afs_soft_proba
from ml.training.features import RAW_FEATURE_COLS, compute_afs_from_row

logger = logging.getLogger(__name__)

_ZONE_NAMES: list[str] = ["green", "yellow", "red"]


@dataclass
class PredictionResult:
    """Computed prediction for a single team-day."""

    afs: float
    resilience_zone: str
    zone_label: int
    probabilities: dict[str, float]
    cold_start: bool
    model_version: str = MODEL_VERSION


def _features_to_row(features: dict[str, float]) -> np.ndarray:
    """Extract RAW_FEATURE_COLS values in canonical order as a 1-D float32 array."""
    return np.array(
        [float(features.get(col, 0.0)) for col in RAW_FEATURE_COLS],
        dtype=np.float32,
    )


def _proba_to_dict(proba: np.ndarray) -> dict[str, float]:
    return {name: round(float(proba[i]), 4) for i, name in enumerate(_ZONE_NAMES)}


class BurnoutPredictor:
    """Stateless predictor wrapping a ModelBundle.

    Args:
        bundle: ModelBundle loaded by :func:`ml.inference.model_loader.load_models`.
    """

    def __init__(self, bundle: ModelBundle) -> None:
        self._bundle = bundle

    def predict(
        self,
        current_features: dict[str, float],
        history: list[dict[str, float]] | None = None,
    ) -> PredictionResult:
        """Predict the resilience zone for a single team-day.

        Args:
            current_features: Dict with keys from RAW_FEATURE_COLS for today.
            history: Optional list of up to 13 prior-day feature dicts
                     (oldest → newest).  Must all have the same keys as
                     ``current_features``.

        Returns:
            PredictionResult with AFS, zone, probabilities, and cold_start flag.
        """
        afs = compute_afs_from_row(current_features)
        afs_arr = np.array([afs], dtype=np.float32)
        p_afs = _afs_soft_proba(afs_arr)[0]  # (3,)

        # ── Warm start: full ensemble ─────────────────────────────────────
        n_history = len(history) if history else 0
        if (
            history is not None
            and n_history >= LSTM_WINDOW_SIZE - 1
            and self._bundle.has_ensemble
        ):
            # Build (1, window_size, n_features) sequence tensor
            context_days = history[-(LSTM_WINDOW_SIZE - 1):]  # last 13 history days
            all_days = [*context_days, current_features]       # + today = 14 days
            X_seq = np.array(
                [[_features_to_row(d) for d in all_days]],
                dtype=np.float32,
            )
            proba = self._bundle.ensemble.predict_proba(X_seq)[0]  # type: ignore[union-attr]
            cold_start = False
            logger.debug("Warm-start prediction: AFS=%.1f", afs)

        # ── Cold start: IF + AFS ──────────────────────────────────────────
        elif self._bundle.has_if:
            X_curr = _features_to_row(current_features).reshape(1, -1)
            p_if = self._bundle.if_model.predict_proba(X_curr)[0]  # type: ignore[union-attr]
            proba = (COLD_START_IF_WEIGHT * p_if + COLD_START_AFS_WEIGHT * p_afs).astype(
                np.float32
            )
            cold_start = True
            logger.debug("Cold-start (IF+AFS) prediction: AFS=%.1f", afs)

        # ── AFS-only fallback ─────────────────────────────────────────────
        else:
            proba = p_afs
            cold_start = True
            logger.debug("AFS-only fallback prediction: AFS=%.1f", afs)

        zone_label = int(proba.argmax())

        return PredictionResult(
            afs=round(float(afs), 2),
            resilience_zone=_ZONE_NAMES[zone_label],
            zone_label=zone_label,
            probabilities=_proba_to_dict(proba),
            cold_start=cold_start,
            model_version=self._bundle.model_version,
        )
