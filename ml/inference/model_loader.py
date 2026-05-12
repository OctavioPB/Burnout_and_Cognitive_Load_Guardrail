"""Model artifact loading for the inference service.

Loads the Sprint 5 artifacts (IF + LSTM + fingerprint) from disk at startup.
Any missing artifact degrades gracefully — the predictor falls back to the
available components (cold-start with IF only, or AFS-only if IF is missing).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ml.inference.config import (
    FINGERPRINT_ARTIFACT,
    IF_ARTIFACT,
    LSTM_ARTIFACT,
    MODEL_DIR,
    MODEL_VERSION,
)
from ml.training.baseline import RuleBasedBaseline
from ml.training.drift_detection import load_fingerprint
from ml.training.ensemble import EnsembleScorer
from ml.training.isolation_forest import BurnoutIsolationForest
from ml.training.lstm_model import LSTMTrainer

logger = logging.getLogger(__name__)


@dataclass
class ModelBundle:
    """All inference-time model objects loaded from disk.

    Components can be None if their artifact file is missing.
    The predictor degrades gracefully based on what is available.
    """

    if_model: BurnoutIsolationForest | None = None
    lstm_trainer: LSTMTrainer | None = None
    ensemble: EnsembleScorer | None = None
    baseline: RuleBasedBaseline = field(default_factory=RuleBasedBaseline)
    fingerprint: dict[str, Any] | None = None
    model_version: str = MODEL_VERSION

    @property
    def has_if(self) -> bool:
        return self.if_model is not None

    @property
    def has_lstm(self) -> bool:
        return self.lstm_trainer is not None

    @property
    def has_ensemble(self) -> bool:
        return self.ensemble is not None

    def status(self) -> dict[str, bool]:
        return {
            "isolation_forest": self.has_if,
            "lstm": self.has_lstm,
            "ensemble": self.has_ensemble,
            "baseline": True,
        }


def load_models(model_dir: Path = MODEL_DIR) -> ModelBundle:
    """Load all available model artifacts from *model_dir*.

    Missing files are logged as warnings and replaced with ``None``.

    Args:
        model_dir: Directory containing Sprint 5 artifacts.

    Returns:
        ModelBundle with all available components populated.
    """
    bundle = ModelBundle()

    # Isolation Forest
    if_path = model_dir / IF_ARTIFACT
    if if_path.exists():
        try:
            bundle.if_model = BurnoutIsolationForest.load(if_path)
            logger.info("IsolationForest loaded from %s", if_path)
        except Exception as exc:
            logger.warning("Failed to load IsolationForest: %s", exc)
    else:
        logger.warning("IsolationForest artifact not found at %s — cold-start mode active", if_path)

    # LSTM
    lstm_path = model_dir / LSTM_ARTIFACT
    if lstm_path.exists():
        try:
            bundle.lstm_trainer = LSTMTrainer.load(lstm_path)
            logger.info("LSTM loaded from %s", lstm_path)
        except Exception as exc:
            logger.warning("Failed to load LSTM: %s", exc)
    else:
        logger.warning("LSTM artifact not found at %s — cold-start mode active", lstm_path)

    # Ensemble (requires both IF and LSTM)
    if bundle.if_model is not None and bundle.lstm_trainer is not None:
        bundle.ensemble = EnsembleScorer(bundle.if_model, bundle.lstm_trainer)
        logger.info("EnsembleScorer assembled")

    # Drift fingerprint
    fp_path = model_dir / FINGERPRINT_ARTIFACT
    if fp_path.exists():
        try:
            bundle.fingerprint = load_fingerprint(fp_path)
            logger.info("Feature fingerprint loaded from %s", fp_path)
        except Exception as exc:
            logger.warning("Failed to load fingerprint: %s", exc)

    loaded = [k for k, v in bundle.status().items() if v]
    logger.info("ModelBundle ready — loaded: %s", loaded)
    return bundle
