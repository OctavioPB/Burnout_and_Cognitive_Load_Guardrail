"""End-to-end evaluation script for the Sprint 5 ensemble model.

Trains the full ensemble (IF + LSTM + AFS) on synthetic data and evaluates
on the held-out test split.  Designed to run in < 3 minutes in CI.

Usage
-----
    python -m ml.evaluation.evaluate
    python -m ml.evaluation.evaluate --n-teams 80 --n-days 90 --seed 42
    python -m ml.evaluation.evaluate --output-dir ml/models/v1.0

CI acceptance thresholds (logged as PASS/FAIL)
-----------------------------------------------
    Red Zone precision  >= 0.80
    Red Zone recall     >= 0.75
    Green Zone FPR      <= 0.10
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from ml.training.dataset import temporal_split
from ml.training.drift_detection import compute_feature_fingerprint, save_fingerprint
from ml.training.ensemble import EnsembleScorer
from ml.training.isolation_forest import BurnoutIsolationForest
from ml.training.lstm_model import LSTMTrainer
from ml.training.sequence_dataset import build_sequences, split_sequence_dataset
from ml.training.synthetic import SyntheticDataGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_DEFAULT_MODEL_DIR: Path = Path("ml/models/v1.0")
_LABEL_MAP: dict[str, int] = {"green": 0, "yellow": 1, "red": 2}


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, Any]:
    """Compute accuracy, per-class precision/recall/F1/FPR, and support.

    Args:
        y_true: Ground-truth integer labels (0=green, 1=yellow, 2=red).
        y_pred: Predicted integer labels (same encoding).

    Returns:
        Dict with ``accuracy``, ``per_class`` (one entry per zone), and
        ``n_samples``.
    """
    n = len(y_true)
    accuracy = float((y_pred == y_true).sum() / n) if n > 0 else 0.0

    zone_names = ["green", "yellow", "red"]
    per_class: dict[str, Any] = {}
    for label, name in enumerate(zone_names):
        tp = int(((y_pred == label) & (y_true == label)).sum())
        fp = int(((y_pred == label) & (y_true != label)).sum())
        fn = int(((y_pred != label) & (y_true == label)).sum())
        tn = int(((y_pred != label) & (y_true != label)).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        per_class[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "fpr": round(fpr, 4),
            "support": int((y_true == label).sum()),
        }

    return {"accuracy": round(accuracy, 4), "per_class": per_class, "n_samples": n}


def train_and_evaluate(
    n_teams: int = 80,
    n_days: int = 90,
    seed: int = 42,
    output_dir: Path = _DEFAULT_MODEL_DIR,
    lstm_max_epochs: int = 20,
    lstm_patience: int = 5,
) -> dict[str, Any]:
    """Train the full ensemble on synthetic data and evaluate on the test split.

    Args:
        n_teams: Synthetic team count.
        n_days: Synthetic day count per team.
        seed: Random seed for data generation and model training.
        output_dir: Directory where all artifacts (models, metrics, fingerprint) are saved.
        lstm_max_epochs: Maximum LSTM training epochs.
        lstm_patience: Early stopping patience for LSTM.

    Returns:
        Metrics dict with per-model and ensemble evaluation results.
    """
    logger.info(
        "Generating synthetic data — n_teams=%d  n_days=%d  seed=%d",
        n_teams, n_days, seed,
    )
    df = SyntheticDataGenerator(seed=seed).generate_dataframe(
        n_teams=n_teams, n_days=n_days
    )

    # ── Tabular split (IF + baseline) ─────────────────────────────────────────
    split = temporal_split(df)
    logger.info(
        "Tabular split: train=%d  val=%d  test=%d",
        split.n_train, split.n_val, split.n_test,
    )

    # ── Sequence split (LSTM + ensemble) ─────────────────────────────────────
    seq_ds = build_sequences(df)
    seq_train, seq_val, seq_test = split_sequence_dataset(
        seq_ds, split.train_end_date, split.val_end_date
    )
    logger.info(
        "Sequence split: train=%d  val=%d  test=%d",
        seq_train.n_sequences, seq_val.n_sequences, seq_test.n_sequences,
    )

    # ── Isolation Forest ──────────────────────────────────────────────────────
    logger.info("Training IsolationForest...")
    if_model = BurnoutIsolationForest(random_state=seed)
    if_model.fit(split.X_train)
    if_metrics = classification_metrics(split.y_test, if_model.predict(split.X_test))
    logger.info(
        "IF — accuracy=%.4f  red_precision=%.4f  red_recall=%.4f",
        if_metrics["accuracy"],
        if_metrics["per_class"]["red"]["precision"],
        if_metrics["per_class"]["red"]["recall"],
    )

    # ── LSTM ──────────────────────────────────────────────────────────────────
    lstm_metrics: dict[str, Any] = {"accuracy": 0.0, "per_class": {}, "n_samples": 0}
    lstm_trainer = LSTMTrainer(
        max_epochs=lstm_max_epochs,
        patience=lstm_patience,
        device="auto",
    )

    if seq_train.n_sequences > 0 and seq_val.n_sequences > 0:
        logger.info("Training LSTM...")
        lstm_trainer.fit(seq_train.X, seq_train.y, seq_val.X, seq_val.y)

        if seq_test.n_sequences > 0:
            lstm_metrics = classification_metrics(
                seq_test.y, lstm_trainer.predict(seq_test.X)
            )
        logger.info("LSTM — accuracy=%.4f", lstm_metrics["accuracy"])
    else:
        logger.warning("Insufficient sequence data for LSTM training — skipping.")

    # ── Ensemble ──────────────────────────────────────────────────────────────
    ensemble_metrics: dict[str, Any] = if_metrics  # fallback if LSTM unavailable

    if lstm_trainer.model is not None and seq_test.n_sequences > 0:
        logger.info("Evaluating ensemble on test sequences...")
        ensemble = EnsembleScorer(if_model, lstm_trainer)
        ensemble_preds = ensemble.predict(seq_test.X)
        ensemble_metrics = classification_metrics(seq_test.y, ensemble_preds)
        logger.info(
            "Ensemble — accuracy=%.4f  red_precision=%.4f  red_recall=%.4f",
            ensemble_metrics["accuracy"],
            ensemble_metrics["per_class"].get("red", {}).get("precision", 0.0),
            ensemble_metrics["per_class"].get("red", {}).get("recall", 0.0),
        )

    # ── Drift fingerprint ─────────────────────────────────────────────────────
    logger.info("Computing feature distribution fingerprint...")
    fingerprint = compute_feature_fingerprint(split.X_train)
    save_fingerprint(fingerprint, output_dir / "fingerprint.json")

    # ── Save model artifacts ──────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    if_model.save(output_dir / "isolation_forest.joblib")
    if lstm_trainer.model is not None:
        lstm_trainer.save(output_dir / "lstm.pt")

    # ── Write metrics report ──────────────────────────────────────────────────
    metrics: dict[str, Any] = {
        "seed": seed,
        "n_teams": n_teams,
        "n_days": n_days,
        "split_summary": split.summary(),
        "isolation_forest": if_metrics,
        "lstm": lstm_metrics,
        "ensemble": ensemble_metrics,
    }
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    logger.info("Metrics written to %s", metrics_path)

    # ── CI acceptance check ───────────────────────────────────────────────────
    red = ensemble_metrics.get("per_class", {}).get("red", {})
    green = ensemble_metrics.get("per_class", {}).get("green", {})
    if red and green:
        checks = {
            "red_precision_ge_0.80": red.get("precision", 0.0) >= 0.80,
            "red_recall_ge_0.75": red.get("recall", 0.0) >= 0.75,
            "green_fpr_le_0.10": green.get("fpr", 1.0) <= 0.10,
        }
        for check_name, passed in checks.items():
            logger.info("CI check %-35s %s", check_name, "PASS" if passed else "FAIL")

    return metrics


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Burnout Guardrail — Sprint 5 Model Evaluation"
    )
    parser.add_argument("--n-teams", type=int, default=80)
    parser.add_argument("--n-days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_MODEL_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    train_and_evaluate(
        n_teams=_args.n_teams,
        n_days=_args.n_days,
        seed=_args.seed,
        output_dir=_args.output_dir,
    )
