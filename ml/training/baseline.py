"""Rule-based baseline model for benchmarking.

The baseline classifies a team's ResilienceZone using hard thresholds on the
four raw features without any learned parameters.  It serves two purposes:

  1. A performance floor that the ML anomaly detection model must beat.
  2. A sanity-check: if the ML model cannot outperform this, the features
     or labels have a problem, not the model choice.

Thresholds are set so the baseline mirrors the AFS zone boundaries mapped
back onto individual features.  Any single feature exceeding its Red threshold
triggers a Red classification (pessimistic / safety-first), while both
green thresholds together are required for a Green classification.

Baseline metrics are saved to ml/models/baseline/metrics.json on evaluation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from ml.training.features import (
    RAW_FEATURE_COLS,
    ResilienceZone,
    afs_to_zone,
    compute_afs,
)

logger = logging.getLogger(__name__)

# ── Threshold tables ──────────────────────────────────────────────────────────
# Any single feature above the RED threshold → Red zone.
# All features below the GREEN threshold  → Green zone.
# Otherwise → Yellow zone.

_RED_THRESHOLDS: dict[str, float] = {
    "calendar_density_score": 0.65,
    "after_hours_activity_index": 0.50,
    "context_switch_count": 0.60,
    "sprint_health_index": 0.30,   # LOW sprint health is bad (inverted)
}

_GREEN_THRESHOLDS: dict[str, float] = {
    "calendar_density_score": 0.30,
    "after_hours_activity_index": 0.15,
    "context_switch_count": 0.25,
    "sprint_health_index": 0.70,   # HIGH sprint health is good
}


class RuleBasedBaseline:
    """Deterministic threshold classifier over RAW_FEATURE_COLS.

    Args:
        red_thresholds: Per-feature values that trigger Red classification.
        green_thresholds: Per-feature values required for Green classification.
    """

    def __init__(
        self,
        red_thresholds: dict[str, float] | None = None,
        green_thresholds: dict[str, float] | None = None,
    ) -> None:
        self._red = red_thresholds or _RED_THRESHOLDS
        self._green = green_thresholds or _GREEN_THRESHOLDS

    # ── Single-record prediction ───────────────────────────────────────────

    def predict_one(self, features: dict[str, float | None]) -> ResilienceZone:
        """Classify a single team-day feature dict.

        Args:
            features: Dict with keys from RAW_FEATURE_COLS.
                      Missing values default to 0.0 (neutral for most features).

        Returns:
            ResilienceZone classification.
        """
        cds = float(features.get("calendar_density_score") or 0.0)
        ahai = float(features.get("after_hours_activity_index") or 0.0)
        csc = float(features.get("context_switch_count") or 0.0)
        shi = float(features.get("sprint_health_index") or 0.5)

        # Any high-risk feature → Red (pessimistic, safety-first)
        if (
            cds >= self._red["calendar_density_score"]
            or ahai >= self._red["after_hours_activity_index"]
            or csc >= self._red["context_switch_count"]
            or shi <= self._red["sprint_health_index"]  # low SHI = bad
        ):
            return ResilienceZone.RED

        # All low-risk features → Green
        if (
            cds < self._green["calendar_density_score"]
            and ahai < self._green["after_hours_activity_index"]
            and csc < self._green["context_switch_count"]
            and shi > self._green["sprint_health_index"]  # high SHI = good
        ):
            return ResilienceZone.GREEN

        return ResilienceZone.YELLOW

    # ── Batch prediction ──────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for a feature matrix.

        Args:
            X: Float32 array of shape (n_samples, n_features).
               Column order must match RAW_FEATURE_COLS.

        Returns:
            Integer array of shape (n_samples,) with values 0 (green),
            1 (yellow), or 2 (red).
        """
        if X.shape[1] != len(RAW_FEATURE_COLS):
            raise ValueError(
                f"Expected {len(RAW_FEATURE_COLS)} features, got {X.shape[1]}"
            )

        results = np.empty(X.shape[0], dtype=np.int32)
        for i, row in enumerate(X):
            feat = dict(zip(RAW_FEATURE_COLS, row.tolist()))
            results[i] = self.predict_one(feat).label
        return results

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(
        self,
        X: np.ndarray,
        y_true: np.ndarray,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Compute precision, recall, F1, and accuracy per zone.

        Args:
            X: Feature matrix.
            y_true: True integer labels (0=green, 1=yellow, 2=red).
            output_path: If provided, write metrics JSON to this path.

        Returns:
            Dict with overall accuracy and per-class precision/recall/f1.
        """
        y_pred = self.predict(X)
        n = len(y_true)
        accuracy = float((y_pred == y_true).sum() / n)

        zone_names = ["green", "yellow", "red"]
        per_class: dict[str, dict[str, float]] = {}
        for label, name in enumerate(zone_names):
            tp = int(((y_pred == label) & (y_true == label)).sum())
            fp = int(((y_pred == label) & (y_true != label)).sum())
            fn = int(((y_pred != label) & (y_true == label)).sum())

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )
            per_class[name] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": int((y_true == label).sum()),
            }

        metrics: dict[str, Any] = {
            "model": "RuleBasedBaseline",
            "accuracy": round(accuracy, 4),
            "per_class": per_class,
            "n_samples": n,
        }

        logger.info(
            "Baseline — accuracy=%.4f  red_precision=%.4f  red_recall=%.4f",
            accuracy,
            per_class["red"]["precision"],
            per_class["red"]["recall"],
        )

        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(metrics, indent=2))
            logger.info("Metrics written to %s", output_path)

        return metrics
