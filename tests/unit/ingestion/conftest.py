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
    """Stub confluent_kafka.Producer for producer unit tests."""
    mock = MagicMock()
    mock.flush.return_value = 0  # 0 = all messages delivered
    return mock


@pytest.fixture()
def async_http_client() -> httpx.AsyncClient:
    """Real AsyncClient — respx patches it at transport level per test."""
    return httpx.AsyncClient()
