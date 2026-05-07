"""Calendar Density Score (CDS) transform.

CDS = total_meeting_minutes / (team_size × WORK_MINUTES_PER_DAY), clamped [0, 1].
High CDS (→ 1.0) means the team is in back-to-back meetings all day.
"""

from __future__ import annotations

from ingestion.models import CalendarActivityEvent

_WORK_MINUTES_PER_DAY: int = 480  # 8-hour workday


def compute_calendar_density_score(
    events: list[CalendarActivityEvent],
    team_size: int,
) -> float:
    """Aggregate meeting load for a team on a single day, normalized per person.

    Args:
        events: All CalendarActivityEvent records for the team on the target date.
        team_size: Number of people in the team unit (denominator for per-person normalization).

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 when events is empty or team_size ≤ 0.
    """
    if not events or team_size <= 0:
        return 0.0

    total_minutes = sum(e.total_meeting_minutes for e in events)
    denominator = team_size * _WORK_MINUTES_PER_DAY
    return min(total_minutes / denominator, 1.0)
