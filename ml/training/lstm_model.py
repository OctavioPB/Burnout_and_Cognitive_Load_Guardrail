"""LSTM sequence model for burnout trend detection.

Trained on 14-day rolling windows of team feature vectors, the LSTM captures
temporal deterioration patterns — e.g. a team steadily shifting from Green to
Yellow over two weeks — that point-in-time models miss.

Architecture
------------
    Input  (batch, window_size, n_features)
    LSTM   num_layers=2 × hidden_size=64, batch_first=True
    Linear 64 → 32 → 3 (logits; CrossEntropyLoss takes logits directly)
    Softmax applied at inference time only

Training
--------
Uses Adam with early stopping on validation loss.  Best weights are restored
after training so the model checkpoint corresponds to the lowest val loss, not
the final epoch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

_DEFAULT_HIDDEN_SIZE: int = 64
_DEFAULT_NUM_LAYERS: int = 2
_DEFAULT_DROPOUT: float = 0.2
_DEFAULT_LR: float = 1e-3
_DEFAULT_BATCH_SIZE: int = 64
_DEFAULT_MAX_EPOCHS: int = 30
_DEFAULT_PATIENCE: int = 5


class BurnoutLSTM(nn.Module):
    """Multi-layer LSTM classifier for resilience zone prediction.

    Args:
        input_size: Number of features per timestep.
        hidden_size: LSTM hidden state dimension.
        num_layers: Number of stacked LSTM layers.
        num_classes: Number of output classes (3: green, yellow, red).
        dropout: Dropout applied between LSTM layers (ignored when num_layers=1).
    """

    def __init__(
        self,
        input_size: int = 4,
        hidden_size: int = _DEFAULT_HIDDEN_SIZE,
        num_layers: int = _DEFAULT_NUM_LAYERS,
        num_classes: int = 3,
        dropout: float = _DEFAULT_DROPOUT,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        lstm_dropout = dropout if num_layers > 1 else 0.0
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=lstm_dropout,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: (batch, seq_len, input_size) tensor.

        Returns:
            Logits of shape (batch, num_classes).
        """
        _, (h_n, _) = self.lstm(x)
        return self.head(h_n[-1])  # last layer's hidden state


@dataclass
class TrainResult:
    """Summary of a completed LSTM training run."""

    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float("inf")


class LSTMTrainer:
    """Manages the LSTM training loop with early stopping.

    Args:
        hidden_size: LSTM hidden dimension.
        num_layers: Number of LSTM layers.
        dropout: Dropout rate applied inside the network.
        lr: Adam learning rate.
        batch_size: Training batch size.
        max_epochs: Maximum training epochs.
        patience: Early stopping patience (epochs without val improvement).
        device: ``'cpu'``, ``'cuda'``, or ``'auto'`` to detect automatically.
    """

    def __init__(
        self,
        hidden_size: int = _DEFAULT_HIDDEN_SIZE,
        num_layers: int = _DEFAULT_NUM_LAYERS,
        dropout: float = _DEFAULT_DROPOUT,
        lr: float = _DEFAULT_LR,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        max_epochs: int = _DEFAULT_MAX_EPOCHS,
        patience: int = _DEFAULT_PATIENCE,
        device: str = "auto",
    ) -> None:
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.lr = lr
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self._device = self._resolve_device(device)
        self.model: BurnoutLSTM | None = None

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> TrainResult:
        """Train the LSTM model with early stopping.

        Args:
            X_train: (n_train, seq_len, n_features) float32 array.
            y_train: (n_train,) int32 label array.
            X_val: (n_val, seq_len, n_features) float32 array.
            y_val: (n_val,) int32 label array.

        Returns:
            TrainResult with loss history and best epoch info.

        Raises:
            ValueError: If input arrays have incompatible shapes.
        """
        if X_train.ndim != 3:
            raise ValueError(f"X_train must be 3-D (n, seq, feat); got shape {X_train.shape}")

        n_features = X_train.shape[2]
        self.model = BurnoutLSTM(
            input_size=n_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        ).to(self._device)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()

        train_loader = self._make_loader(X_train, y_train, shuffle=True)
        val_loader = self._make_loader(X_val, y_val, shuffle=False)

        result = TrainResult()
        best_state: dict[str, Any] = {}
        patience_counter = 0

        for epoch in range(self.max_epochs):
            train_loss = self._run_epoch(train_loader, optimizer, criterion, train=True)
            val_loss = self._run_epoch(val_loader, optimizer, criterion, train=False)

            result.train_losses.append(train_loss)
            result.val_losses.append(val_loss)

            if val_loss < result.best_val_loss:
                result.best_val_loss = val_loss
                result.best_epoch = epoch
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            logger.debug(
                "Epoch %d/%d — train=%.4f  val=%.4f",
                epoch + 1,
                self.max_epochs,
                train_loss,
                val_loss,
            )

            if patience_counter >= self.patience:
                logger.info("Early stopping at epoch %d (patience=%d)", epoch + 1, self.patience)
                break

        if best_state:
            self.model.load_state_dict({k: v.to(self._device) for k, v in best_state.items()})

        logger.info(
            "Training complete — best_epoch=%d  best_val_loss=%.4f",
            result.best_epoch,
            result.best_val_loss,
        )
        return result

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return softmax class probabilities.

        Args:
            X: (n_samples, seq_len, n_features) float32 array.

        Returns:
            Float32 array of shape (n_samples, 3).
        """
        self._check_fitted()
        self.model.eval()  # type: ignore[union-attr]
        tensor = torch.from_numpy(X).float().to(self._device)
        with torch.no_grad():
            logits = self.model(tensor)  # type: ignore[misc]
            proba = torch.softmax(logits, dim=1).cpu().numpy()
        return proba.astype(np.float32)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return integer class predictions (0=green, 1=yellow, 2=red).

        Args:
            X: (n_samples, seq_len, n_features) float32 array.

        Returns:
            Int32 array of shape (n_samples,).
        """
        return self.predict_proba(X).argmax(axis=1).astype(np.int32)

    # ── Serialization ─────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """Save model weights and architecture config to a .pt file.

        Args:
            path: Destination file path (parent dirs created if needed).
        """
        self._check_fitted()
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),  # type: ignore[union-attr]
                "config": {
                    "input_size": self.model.lstm.input_size,  # type: ignore[union-attr]
                    "hidden_size": self.hidden_size,
                    "num_layers": self.num_layers,
                    "dropout": self.dropout,
                },
            },
            path,
        )
        logger.info("LSTM saved to %s", path)

    @classmethod
    def load(cls, path: Path) -> "LSTMTrainer":
        """Load a trainer with a pre-trained LSTM ready for inference.

        Args:
            path: File produced by :meth:`save`.

        Returns:
            LSTMTrainer instance with model loaded and set to eval mode.
        """
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        cfg = checkpoint["config"]
        obj = cls(
            hidden_size=cfg["hidden_size"],
            num_layers=cfg["num_layers"],
            dropout=cfg["dropout"],
            device="cpu",
        )
        obj.model = BurnoutLSTM(**cfg)
        obj.model.load_state_dict(checkpoint["model_state_dict"])
        obj.model.eval()
        return obj

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_loader(
        self, X: np.ndarray, y: np.ndarray, shuffle: bool
    ) -> DataLoader:  # type: ignore[type-arg]
        tensor_X = torch.from_numpy(X).float()
        tensor_y = torch.from_numpy(y).long()
        return DataLoader(
            TensorDataset(tensor_X, tensor_y),
            batch_size=self.batch_size,
            shuffle=shuffle,
        )

    def _run_epoch(
        self,
        loader: DataLoader,  # type: ignore[type-arg]
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        train: bool,
    ) -> float:
        self.model.train(train)  # type: ignore[union-attr]
        total_loss = 0.0
        n_samples = 0
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(self._device)
            y_batch = y_batch.to(self._device)
            if train:
                optimizer.zero_grad()
            logits = self.model(X_batch)  # type: ignore[misc]
            loss = criterion(logits, y_batch)
            if train:
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * len(y_batch)
            n_samples += len(y_batch)
        return total_loss / max(n_samples, 1)

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device)

    def _check_fitted(self) -> None:
        if self.model is None:
            raise RuntimeError(
                "LSTMTrainer must call fit() before calling predict methods."
            )
