"""Feature distribution fingerprinting for data drift detection.

A fingerprint is a snapshot of per-feature statistics (mean, std, percentiles)
captured on the training set immediately after model training.  At serving
time, incoming batch statistics are compared against the fingerprint; features
that deviate by more than ``threshold`` standard deviations from the training
mean trigger a drift alert.

Usage in the inference pipeline (Sprint 6)
------------------------------------------
    # At training time:
    fp = compute_feature_fingerprint(split.X_train)
    save_fingerprint(fp, Path("ml/models/v1.0/fingerprint.json"))

    # At serving time (inside the scoring endpoint):
    fp = load_fingerprint(Path("ml/models/v1.0/fingerprint.json"))
    report = check_drift(incoming_X, fp)
    if report["any_drift"]:
        alert_oncall(report["drifted_features"])
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from ml.training.features import RAW_FEATURE_COLS

logger = logging.getLogger(__name__)

_PERCENTILES: list[int] = [5, 25, 50, 75, 95]
_DEFAULT_DRIFT_THRESHOLD: float = 2.0  # z-score cutoff for drift alerts


def compute_feature_fingerprint(
    X: np.ndarray,
    feature_names: list[str] | None = None,
) -> dict[str, Any]:
    """Compute per-feature distribution statistics from a training feature matrix.

    Args:
        X: Float array of shape (n_samples, n_features).
        feature_names: Optional column names.  Defaults to RAW_FEATURE_COLS.

    Returns:
        Dict with keys:
          - ``n_samples``: int
          - ``n_features``: int
          - ``features``: {name: {mean, std, min, max, percentiles}}
    """
    if feature_names is None:
        feature_names = RAW_FEATURE_COLS

    stats: dict[str, Any] = {}
    for i, name in enumerate(feature_names):
        col = X[:, i].astype(float)
        pcts = np.percentile(col, _PERCENTILES).tolist()
        stats[name] = {
            "mean": float(np.mean(col)),
            "std": float(np.std(col)),
            "min": float(np.min(col)),
            "max": float(np.max(col)),
            "percentiles": {str(p): float(v) for p, v in zip(_PERCENTILES, pcts, strict=False)},
        }

    return {
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "features": stats,
    }


def save_fingerprint(fingerprint: dict[str, Any], path: Path) -> None:
    """Serialize a fingerprint dict to a JSON file.

    Args:
        fingerprint: Dict produced by :func:`compute_feature_fingerprint`.
        path: Destination file path (parent directories created if needed).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fingerprint, indent=2))
    logger.info("Feature fingerprint saved to %s", path)


def load_fingerprint(path: Path) -> dict[str, Any]:
    """Load a fingerprint from a JSON file.

    Args:
        path: File produced by :func:`save_fingerprint`.

    Returns:
        Fingerprint dict.
    """
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def check_drift(
    X_new: np.ndarray,
    fingerprint: dict[str, Any],
    feature_names: list[str] | None = None,
    threshold: float = _DEFAULT_DRIFT_THRESHOLD,
) -> dict[str, Any]:
    """Compare incoming feature statistics against the training fingerprint.

    For each feature, the new batch mean is compared to the training mean using
    the training standard deviation as the scale.  A z-score above ``threshold``
    indicates drift.

    Args:
        X_new: Incoming feature array of shape (n_samples, n_features).
        fingerprint: Dict produced by :func:`compute_feature_fingerprint`.
        feature_names: Column names for X_new.  Defaults to RAW_FEATURE_COLS.
        threshold: Drift threshold in units of training standard deviations.

    Returns:
        Dict with keys:
          - ``any_drift``: bool
          - ``drifted_features``: list[str]
          - ``drift_details``: {feature: {ref_mean, new_mean, z_score, drifted}}
          - ``threshold``: float
    """
    if feature_names is None:
        feature_names = RAW_FEATURE_COLS

    drift_details: dict[str, dict[str, float]] = {}
    drifted: list[str] = []

    for i, name in enumerate(feature_names):
        if name not in fingerprint.get("features", {}):
            continue
        ref = fingerprint["features"][name]
        new_mean = float(np.mean(X_new[:, i]))
        # Guard against constant features (std ≈ 0) to avoid division by zero
        ref_std = max(float(ref["std"]), 1e-8)
        z_score = abs(new_mean - float(ref["mean"])) / ref_std

        is_drifted = bool(z_score > threshold)
        drift_details[name] = {
            "ref_mean": float(ref["mean"]),
            "new_mean": round(new_mean, 6),
            "z_score": round(z_score, 4),
            "drifted": float(is_drifted),  # stored as float for JSON serialisation
        }
        if is_drifted:
            drifted.append(name)
            logger.warning(
                "Drift detected on '%s': z=%.2f (threshold=%.1f)", name, z_score, threshold
            )

    return {
        "any_drift": len(drifted) > 0,
        "drifted_features": drifted,
        "drift_details": drift_details,
        "threshold": threshold,
    }
