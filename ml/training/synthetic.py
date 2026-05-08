"""Synthetic data generator for local development and CI.

Produces statistically plausible TeamDayFeatureRecord rows without requiring
a live data warehouse.  The generator uses parameterized Gaussian distributions
per ResilienceZone so the synthetic dataset reflects realistic cluster structure.

Usage:
    from ml.training.synthetic import SyntheticDataGenerator

    gen = SyntheticDataGenerator(seed=42)
    df = gen.generate_dataframe(n_teams=20, n_days=30)
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ml.training.features import (
    AFS_COL,
    RAW_FEATURE_COLS,
    ZONE_COL,
    ResilienceZone,
    TeamDayFeatureRecord,
    afs_to_zone,
    compute_afs,
)

# ── Per-zone distribution parameters ─────────────────────────────────────────
# Each entry: { feature: (mean, std) }
# Values are clipped to [0, 1] after sampling.

_ZONE_PARAMS: dict[ResilienceZone, dict[str, tuple[float, float]]] = {
    ResilienceZone.GREEN: {
        "calendar_density_score": (0.20, 0.08),
        "after_hours_activity_index": (0.05, 0.04),
        "context_switch_count": (0.15, 0.07),
        "sprint_health_index": (0.80, 0.10),
    },
    ResilienceZone.YELLOW: {
        "calendar_density_score": (0.45, 0.10),
        "after_hours_activity_index": (0.25, 0.10),
        "context_switch_count": (0.40, 0.10),
        "sprint_health_index": (0.55, 0.12),
    },
    ResilienceZone.RED: {
        "calendar_density_score": (0.72, 0.10),
        "after_hours_activity_index": (0.55, 0.12),
        "context_switch_count": (0.70, 0.10),
        "sprint_health_index": (0.25, 0.12),
    },
}

# Default zone distribution: roughly mirrors a healthy org (most teams green)
_DEFAULT_ZONE_WEIGHTS: dict[ResilienceZone, float] = {
    ResilienceZone.GREEN: 0.55,
    ResilienceZone.YELLOW: 0.30,
    ResilienceZone.RED: 0.15,
}


class SyntheticDataGenerator:
    """Generate statistically plausible synthetic feature records.

    Args:
        seed: Random seed for reproducibility.
        zone_weights: Fraction of records per ResilienceZone.
                      Defaults to 55 % green / 30 % yellow / 15 % red.
    """

    def __init__(
        self,
        seed: int = 42,
        zone_weights: dict[ResilienceZone, float] | None = None,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._zone_weights = zone_weights or _DEFAULT_ZONE_WEIGHTS

        total = sum(self._zone_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"zone_weights must sum to 1.0, got {total:.4f}")

    # ── Core sampling ─────────────────────────────────────────────────────────

    def _sample_zone(self) -> ResilienceZone:
        zones = list(self._zone_weights.keys())
        probs = [self._zone_weights[z] for z in zones]
        idx = int(self._rng.choice(len(zones), p=probs))
        return zones[idx]

    def _sample_features(self, zone: ResilienceZone) -> dict[str, float]:
        params = _ZONE_PARAMS[zone]
        result: dict[str, float] = {}
        for col in RAW_FEATURE_COLS:
            mean, std = params[col]
            val = float(self._rng.normal(mean, std))
            result[col] = float(np.clip(val, 0.0, 1.0))
        return result

    def generate_record(
        self,
        team_id: str,
        workspace_id: str,
        date_utc: str,
        zone: ResilienceZone | None = None,
    ) -> TeamDayFeatureRecord:
        """Sample one TeamDayFeatureRecord.

        Args:
            team_id: Team identifier string.
            workspace_id: Workspace identifier string.
            date_utc: ISO-8601 date string (YYYY-MM-DD).
            zone: Force a specific zone. When None, sampled from zone_weights.

        Returns:
            A fully populated TeamDayFeatureRecord with AFS and zone computed.
        """
        if zone is None:
            zone = self._sample_zone()
        features = self._sample_features(zone)
        return TeamDayFeatureRecord(
            team_id=team_id,
            workspace_id=workspace_id,
            date_utc=date_utc,
            **features,
        )

    # ── Bulk generation ───────────────────────────────────────────────────────

    def generate_records(
        self,
        n_teams: int = 10,
        n_days: int = 30,
        start_date: date | None = None,
        workspace_id: str = "W_SYNTHETIC",
    ) -> list[TeamDayFeatureRecord]:
        """Generate a cross-join of n_teams × n_days records.

        Each team gets a consistent zone bias across time (simulating stable
        team states) with small day-to-day noise from the Gaussian sampling.

        Args:
            n_teams: Number of distinct synthetic teams.
            n_days: Number of consecutive days per team.
            start_date: First date in the range. Defaults to 30 days before today.
            workspace_id: Workspace identifier applied to all records.

        Returns:
            List of TeamDayFeatureRecord, ordered by team then date.
        """
        if start_date is None:
            from datetime import date as _date

            start_date = _date.today() - timedelta(days=n_days)

        # Assign a persistent zone bias per team
        team_zones = [self._sample_zone() for _ in range(n_teams)]

        records: list[TeamDayFeatureRecord] = []
        for t_idx in range(n_teams):
            team_id = f"T_SYN_{t_idx:03d}"
            zone_bias = team_zones[t_idx]
            for d in range(n_days):
                date_str = (start_date + timedelta(days=d)).isoformat()
                # 80 % chance to stay in the team's base zone, 20 % random drift
                zone = zone_bias if self._rng.random() < 0.80 else self._sample_zone()
                records.append(
                    self.generate_record(team_id, workspace_id, date_str, zone=zone)
                )
        return records

    def generate_dataframe(
        self,
        n_teams: int = 10,
        n_days: int = 30,
        start_date: date | None = None,
        workspace_id: str = "W_SYNTHETIC",
    ) -> pd.DataFrame:
        """Generate synthetic data as a pandas DataFrame.

        Columns: team_id, workspace_id, date_utc, all RAW_FEATURE_COLS, afs, resilience_zone.

        Args:
            n_teams: Number of distinct synthetic teams.
            n_days: Number of consecutive days per team.
            start_date: First date in the range. Defaults to 30 days before today.
            workspace_id: Workspace identifier applied to all records.

        Returns:
            DataFrame with shape (n_teams * n_days, 9).
        """
        records = self.generate_records(n_teams, n_days, start_date, workspace_id)
        return pd.DataFrame([r.to_dict() for r in records])
