"""Inference service configuration — model paths and version metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Final

MODEL_VERSION: Final[str] = "v1.0"
MODEL_DIR: Final[Path] = Path("ml/models/v1.0")

# Artifact file names inside MODEL_DIR
IF_ARTIFACT: Final[str] = "isolation_forest.joblib"
LSTM_ARTIFACT: Final[str] = "lstm.pt"
FINGERPRINT_ARTIFACT: Final[str] = "fingerprint.json"

# LSTM window size must match the value used during training
LSTM_WINDOW_SIZE: Final[int] = 14

# Cold-start component weights (no LSTM available)
COLD_START_IF_WEIGHT: Final[float] = 0.50
COLD_START_AFS_WEIGHT: Final[float] = 0.50
