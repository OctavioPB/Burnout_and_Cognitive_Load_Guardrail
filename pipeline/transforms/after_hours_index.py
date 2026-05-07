"""After-Hours Activity Index (AHAI) transform.

AHAI = weighted after-hours messages / weighted total messages, clamped [0, 1].
Weekend activity is weighted × 1.5 because it signals stronger boundary erosion.
"""

from __future__ import annotations

from ingestion.models import SlackActivityEvent

_WEEKEND_WEIGHT: float = 1.5


def compute_after_hours_activity_index(events: list[SlackActivityEvent]) -> float:
    """Proportion of Slack activity occurring outside core hours (before 09:00 or after 18:00 UTC).

    Args:
        events: All SlackActivityEvent records for the team on the target date.
                Each record covers one channel-hour bucket.

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 when events is empty or all messages are
        within business hours.
    """
    if not events:
        return 0.0

    weighted_total = 0.0
    weighted_after_hours = 0.0

    for event in events:
        weight = _WEEKEND_WEIGHT if event.day_of_week >= 5 else 1.0
        weighted = event.message_count * weight
        weighted_total += weighted
        if event.is_after_hours:
            weighted_after_hours += weighted

    if weighted_total == 0.0:
        return 0.0

    return min(weighted_after_hours / weighted_total, 1.0)
