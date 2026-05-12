"""Alert engine: fires when a team spends ≥ 3 consecutive days in Red Zone.

The engine maintains a per-team in-memory state store (dict).  Each processed
prediction either extends the team's consecutive-Red streak or resets it.
When the streak reaches the threshold, an Alert is produced.

Design notes
------------
- State is in-process only.  For production, back the store with Redis to
  survive restarts and support horizontal scaling.  The interface is designed
  to make that swap easy — ``_store`` is typed as a plain dict and can be
  replaced with any mapping.
- Only one alert fires per crossing event: once a team hits the threshold, the
  counter resets to zero so the *next* alert requires another full streak.
- The engine is synchronous; notifications are dispatched by the caller (main.py)
  so that async I/O isn't mixed into state mutation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ml.inference.interventions import Intervention, suggest_interventions

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD: int = 3


@dataclass
class Alert:
    """Fired when a team's consecutive Red Zone streak reaches the threshold."""

    team_id: str
    workspace_id: str
    trigger_date: str
    consecutive_red_days: int
    interventions: list[Intervention]
    features: dict[str, float]


class AlertEngine:
    """Tracks consecutive Red Zone days per team and fires alerts at threshold.

    Args:
        threshold: Number of consecutive Red Zone days required to fire an alert.
        state_store: External mapping for persistence (defaults to an empty dict
                     for in-process use; replace with a Redis-backed mapping for
                     production multi-instance deployments).
    """

    def __init__(
        self,
        threshold: int = _DEFAULT_THRESHOLD,
        state_store: dict[str, int] | None = None,
    ) -> None:
        if threshold < 1:
            raise ValueError(f"threshold must be >= 1; got {threshold}")
        self._threshold = threshold
        # Maps team_id → current consecutive Red day count
        self._store: dict[str, int] = state_store if state_store is not None else {}

    # ── Core method ───────────────────────────────────────────────────────────

    def process(
        self,
        team_id: str,
        workspace_id: str,
        date_utc: str,
        resilience_zone: str,
        features: dict[str, float],
    ) -> Alert | None:
        """Update the streak counter and return an Alert if threshold is reached.

        Args:
            team_id: Team identifier.
            workspace_id: Workspace identifier.
            date_utc: ISO date string for the prediction day.
            resilience_zone: Predicted zone ("green", "yellow", or "red").
            features: Current-day feature dict (used to generate interventions).

        Returns:
            Alert instance if the streak just reached the threshold, else None.
        """
        if resilience_zone == "red":
            self._store[team_id] = self._store.get(team_id, 0) + 1
            streak = self._store[team_id]
            logger.debug("Team %s consecutive Red days: %d", team_id, streak)

            if streak >= self._threshold:
                # Reset counter so the next alert requires a fresh streak
                self._store[team_id] = 0
                interventions = suggest_interventions(features)
                alert = Alert(
                    team_id=team_id,
                    workspace_id=workspace_id,
                    trigger_date=date_utc,
                    consecutive_red_days=streak,
                    interventions=interventions,
                    features=features,
                )
                logger.warning(
                    "Alert fired: team=%s  consecutive_red=%d  date=%s",
                    team_id,
                    streak,
                    date_utc,
                )
                return alert
        else:
            # Non-red day resets the streak
            if self._store.get(team_id, 0) > 0:
                logger.debug("Team %s streak reset (zone=%s)", team_id, resilience_zone)
            self._store[team_id] = 0

        return None

    # ── Inspection ────────────────────────────────────────────────────────────

    def streak(self, team_id: str) -> int:
        """Return the current consecutive Red day count for a team."""
        return self._store.get(team_id, 0)

    def reset(self, team_id: str) -> None:
        """Manually reset the streak counter for a team."""
        self._store[team_id] = 0

    def reset_all(self) -> None:
        """Clear all streak counters (e.g., on service restart)."""
        self._store.clear()
