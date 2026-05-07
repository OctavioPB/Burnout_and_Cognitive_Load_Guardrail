"""Sprint Health Index (SHI) transform.

SHI = delivery_ratio × cycle_time_component, in [0, 1].
1.0 = 100 % sprint delivery + very fast PR review cycle.
None = no data available for either dimension.
"""

from __future__ import annotations

from ingestion.models import GitHubActivityEvent, JiraSprintEvent

_MAX_CYCLE_TIME_HOURS: float = 48.0  # cycle time beyond this maps to component = 0.0


def compute_sprint_health_index(
    jira_events: list[JiraSprintEvent],
    github_events: list[GitHubActivityEvent],
) -> float | None:
    """Combine sprint delivery rate and PR cycle-time velocity into a single index.

    Args:
        jira_events: JiraSprintEvent records covering the target date's active sprints.
        github_events: GitHubActivityEvent records for the team on the target date.

    Returns:
        Float in [0.0, 1.0], or None when both lists are empty (insufficient data).
        When only one source is available the other component defaults to 1.0.
    """
    if not jira_events and not github_events:
        return None

    # Delivery component — ratio of story points completed to committed.
    # No committed points means no sprint debt: treat as fully delivered.
    if jira_events:
        total_committed = sum(e.committed_points for e in jira_events)
        total_completed = sum(e.completed_points for e in jira_events)
        delivery_ratio = (
            min(total_completed / total_committed, 1.0) if total_committed > 0 else 1.0
        )
    else:
        delivery_ratio = 1.0

    # Cycle-time component — lower cycle time → higher component value.
    if github_events:
        cycle_hours = [e.avg_pr_cycle_time_hours for e in github_events]
        avg_cycle = sum(cycle_hours) / len(cycle_hours)
        cycle_time_component = 1.0 - min(avg_cycle / _MAX_CYCLE_TIME_HOURS, 1.0)
    else:
        cycle_time_component = 1.0

    return delivery_ratio * cycle_time_component
