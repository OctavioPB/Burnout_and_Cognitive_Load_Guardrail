"""Shared fixtures for ingestion unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest
import respx

WORKSPACE_ID = "W001"
TEAM_ID = "T001"
SINCE = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
UNTIL = datetime(2024, 1, 16, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def mock_producer() -> MagicMock:
    """Stub confluent_kafka.Producer for producer unit tests.

    Simulates a successful synchronous delivery by invoking the callback
    passed to produce() with (None, mock_msg), so _DeliveryResult.success
    is set to True before flush() is checked.
    """
    mock = MagicMock()
    mock.flush.return_value = 0

    def _produce(topic: str, value: bytes = b"", callback: object = None, **_: object) -> None:
        if callable(callback):
            callback(None, MagicMock())  # err=None signals successful delivery

    mock.produce.side_effect = _produce
    return mock


@pytest.fixture()
def async_http_client() -> httpx.AsyncClient:
    """Real AsyncClient — respx patches it at transport level per test."""
    return httpx.AsyncClient()
