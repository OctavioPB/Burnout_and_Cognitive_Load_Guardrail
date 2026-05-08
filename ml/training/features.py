"""Feature store schema and Attention Fragmentation Score (AFS) computation.

This module is the single source of truth for:
  1. The feature vector layout (column names, dtypes, expected ranges).
  2. The AFS composite formula.
  3. The Resilience Zone mapping from AFS to Green / Yellow / Red.

All downstream code (training, inference, evaluation) imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

import numpy as np

# ── Feature column registry ───────────────────────────────────────────────────

#: Ordered list of raw feature column names produced by pipeline.transforms.
RAW_FEATURE_COLS: Final[list[str]] = [
    "calendar_density_score",       # [0, 1] — meeting saturation
    "after_hours_activity_index",   # [0, 1] — boundary erosion
    "context_switch_count",         # [0, 1] — attention fragmentation
    "sprint_health_index",          # [0, 1] — delivery health (higher = better)
]

#: AFS is derived from RAW_FEATURE_COLS; never stored as a raw feature.
AFS_COL: Final[str] = "afs"
ZONE_COL: Final[str] = "resilience_zone"

#: Full feature + label column set expected in a training DataFrame.
ALL_COLS: Final[list[str]] = RAW_FEATURE_COLS + [AFS_COL, ZONE_COL]

# Expected ranges for validation (inclusive)
FEATURE_RANGES: Final[dict[str, tuple[float, float]]] = {
    "calendar_density_score": (0.0, 1.0),
    "after_hours_activity_index": (0.0, 1.0),
    "context_switch_count": (0.0, 1.0),
    "sprint_health_index": (0.0, 1.0),
    AFS_COL: (0.0, 100.0),
}

# ── AFS weights ───────────────────────────────────────────────────────────────

# Component weights must sum to 1.0.
# sprint_health is inverted (1 - SHI) so all four components have the same
# directionality: higher raw value → higher fragmentation → higher AFS.
AFS_WEIGHTS: Final[dict[str, float]] = {
    "context_switch_count": 0.35,
    "calendar_density_score": 0.30,
    "after_hours_activity_index": 0.25,
    "sprint_health_index": 0.10,   # applied as (1 - sprint_health_index)
}

assert abs(sum(AFS_WEIGHTS.values()) - 1.0) < 1e-9, "AFS weights must sum to 1.0"

# ── Resilience Zone ───────────────────────────────────────────────────────────


class ResilienceZone(str, Enum):
    GREEN = "green"    # AFS  0–39  — Healthy
    YELLOW = "yellow"  # AFS 40–69  — Monitor
    RED = "red"        # AFS 70–100 — Intervene

    @property
    def label(self) -> int:
        """Integer label for ML classification (0 = green, 1 = yellow, 2 = red)."""
        return {"green": 0, "yellow": 1, "red": 2}[self.value]


_ZONE_THRESHOLDS: Final[list[tuple[float, ResilienceZone]]] = [
    (40.0, ResilienceZone.GREEN),
    (70.0, ResilienceZone.YELLOW),
    (101.0, ResilienceZone.RED),
]


def afs_to_zone(afs: float) -> ResilienceZone:
    """Map an AFS score in [0, 100] to a ResilienceZone."""
    for threshold, zone in _ZONE_THRESHOLDS:
        if afs < threshold:
            return zone
    return ResilienceZone.RED  # safety fallback for afs == 100.0


# ── AFS computation ───────────────────────────────────────────────────────────


def compute_afs(
    context_switch_count: float,
    calendar_density_score: float,
    after_hours_activity_index: float,
    sprint_health_index: float | None,
) -> float:
    """Compute the Attention Fragmentation Score for a single team-day.

    Args:
        context_switch_count: [0, 1] from pipeline.transforms.context_switch
        calendar_density_score: [0, 1] from pipeline.transforms.calendar_density
        after_hours_activity_index: [0, 1] from pipeline.transforms.after_hours_index
        sprint_health_index: [0, 1] from pipeline.transforms.sprint_health, or None
                             when insufficient data. Treated as 0.5 (neutral) when None.

    Returns:
        AFS score in [0.0, 100.0].
    """
    shi = sprint_health_index if sprint_health_index is not None else 0.5

    raw = (
        AFS_WEIGHTS["context_switch_count"] * context_switch_count
        + AFS_WEIGHTS["calendar_density_score"] * calendar_density_score
        + AFS_WEIGHTS["after_hours_activity_index"] * after_hours_activity_index
        + AFS_WEIGHTS["sprint_health_index"] * (1.0 - shi)  # invert: low health = high AFS
    )
    return float(np.clip(raw * 100.0, 0.0, 100.0))


def compute_afs_from_row(row: dict[str, float | None]) -> float:
    """Convenience wrapper: compute AFS from a feature dict (e.g. a DataFrame row)."""
    return compute_afs(
        context_switch_count=float(row.get("context_switch_count") or 0.0),
        calendar_density_score=float(row.get("calendar_density_score") or 0.0),
        after_hours_activity_index=float(row.get("after_hours_activity_index") or 0.0),
        sprint_health_index=row.get("sprint_health_index"),
    )


# ── Feature record dataclass ──────────────────────────────────────────────────


@dataclass
class TeamDayFeatureRecord:
    """Fully computed feature record for one (team_id, date_utc)."""

    team_id: str
    workspace_id: str
    date_utc: str

    calendar_density_score: float
    after_hours_activity_index: float
    context_switch_count: float
    sprint_health_index: float | None

    afs: float = field(init=False)
    resilience_zone: ResilienceZone = field(init=False)

    def __post_init__(self) -> None:
        self.afs = compute_afs(
            self.context_switch_count,
            self.calendar_density_score,
            self.after_hours_activity_index,
            self.sprint_health_index,
        )
        self.resilience_zone = afs_to_zone(self.afs)

    def to_dict(self) -> dict[str, object]:
        return {
            "team_id": self.team_id,
            "workspace_id": self.workspace_id,
            "date_utc": self.date_utc,
            "calendar_density_score": self.calendar_density_score,
            "after_hours_activity_index": self.after_hours_activity_index,
            "context_switch_count": self.context_switch_count,
            "sprint_health_index": self.sprint_health_index,
            "afs": self.afs,
            "resilience_zone": self.resilience_zone.value,
        }
