"""Context-Switch Count (CSC) transform.

CSC = (calendar back-to-back pairs + distinct GitHub repos touched) / MAX_DAILY_SWITCHES.
Clamped to [0, 1]. Each forced context change (meeting collision or repo hop) adds cost.
"""

from __future__ import annotations

from ingestion.models import CalendarActivityEvent, GitHubActivityEvent

_MAX_DAILY_SWITCHES: int = 20  # raw switch count that maps to CSC = 1.0


def compute_context_switch_count(
    calendar_events: list[CalendarActivityEvent],
    github_events: list[GitHubActivityEvent],
) -> float:
    """Estimate cognitive context-switching frequency for a team on a single day.

    Back-to-back meeting pairs (< 5 min gap) are the primary signal — each pair
    forces an abrupt task change.  Distinct GitHub repos touched adds a secondary
    signal for code-context fragmentation.

    Args:
        calendar_events: CalendarActivityEvent records for the team on the target date.
        github_events: GitHubActivityEvent records for the team on the target date.

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 when both lists are empty.
    """
    back_to_back = sum(e.back_to_back_count for e in calendar_events)
    distinct_repos = len({e.repo_id for e in github_events if e.repo_id})
    raw = back_to_back + distinct_repos
    return min(raw / _MAX_DAILY_SWITCHES, 1.0)
