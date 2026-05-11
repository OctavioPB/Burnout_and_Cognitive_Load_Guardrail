"""Rule-based intervention suggestions for Red Zone teams.

Each rule maps a feature threshold to a concrete HR action recommendation.
All four raw features are evaluated; multiple interventions can apply
simultaneously if several features are at risk.

Thresholds are aligned with the Red Zone boundaries used in
:mod:`ml.training.baseline` so that interventions are triggered under the
same conditions that cause a Red classification.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intervention:
    """A single suggested HR intervention."""

    id: str
    title: str
    description: str


# ── Threshold rules ───────────────────────────────────────────────────────────
# Each rule is (feature_name, threshold, comparator, Intervention)
# comparator is "ge" (>=) for stress features, "le" (<=) for health features.

_RULES: list[tuple[str, float, str, Intervention]] = [
    (
        "calendar_density_score",
        0.65,
        "ge",
        Intervention(
            id="meeting_free_friday",
            title="Meeting-Free Friday",
            description=(
                "Block all recurring meetings on Fridays for 4 weeks to restore "
                "deep-work time. Enforce via calendar policy in the workspace."
            ),
        ),
    ),
    (
        "after_hours_activity_index",
        0.60,
        "ge",
        Intervention(
            id="async_first_week",
            title="Async-First Week",
            description=(
                "Disable Slack notifications after 18:00 and mandate async "
                "responses for all non-urgent communication for one week."
            ),
        ),
    ),
    (
        "sprint_health_index",
        0.50,
        "le",
        Intervention(
            id="load_redistribution",
            title="Load Redistribution Review",
            description=(
                "Schedule a team capacity review with the engineering lead to "
                "redistribute story points and reduce sprint commitments by ≥ 20%."
            ),
        ),
    ),
    (
        "context_switch_count",
        0.60,
        "ge",
        Intervention(
            id="focus_blocks",
            title="Deep Work Blocks",
            description=(
                "Reserve 2-hour uninterruptible focus blocks three mornings per "
                "week. Block calendars and disable notifications during these windows."
            ),
        ),
    ),
]


def suggest_interventions(features: dict[str, float]) -> list[Intervention]:
    """Return applicable HR intervention suggestions for a given feature set.

    Args:
        features: Dict with RAW_FEATURE_COLS keys and float values in [0, 1].

    Returns:
        List of Intervention objects whose threshold conditions are met.
        Empty list if no threshold is exceeded (team is not in a critical zone).
    """
    result: list[Intervention] = []
    for feature_name, threshold, comparator, intervention in _RULES:
        raw = features.get(feature_name)
        if raw is None:
            continue  # no data for this feature — don't trigger the rule
        value = float(raw)
        triggered = (comparator == "ge" and value >= threshold) or (
            comparator == "le" and value <= threshold
        )
        if triggered:
            result.append(intervention)
    return result
