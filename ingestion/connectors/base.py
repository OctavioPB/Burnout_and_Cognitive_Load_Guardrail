"""Abstract base class for all digital exhaust connectors."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

import httpx
from pydantic import BaseModel

E = TypeVar("E", bound=BaseModel)


class BaseConnector(ABC, Generic[E]):
    """
    Abstract interface for fetching metadata-only signals from collaboration tools.

    Contract:
    - fetch_events() MUST NOT capture message/document content, user names,
      or any other personal data — only timestamps, counts, and durations.
    - The http_client is injected (not created internally) to allow test mocking
      and lifecycle management by the caller.
    """

    def __init__(
        self,
        workspace_id: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._workspace_id = workspace_id
        self._http = http_client
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def fetch_events(
        self,
        team_id: str,
        since: datetime,
        until: datetime,
    ) -> list[E]:
        """Fetch metadata events for a team within [since, until).

        Args:
            team_id: Internal team unit identifier.
            since:   Inclusive start of the fetch window (UTC).
            until:   Exclusive end of the fetch window (UTC).

        Returns:
            List of typed events. Empty list when no activity in the window.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the upstream API is reachable and credentials are valid."""
        ...
