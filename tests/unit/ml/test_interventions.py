"""Unit tests for ml.inference.interventions — suggest_interventions."""

from __future__ import annotations

from ml.inference.interventions import Intervention, suggest_interventions

# ── Fixtures ──────────────────────────────────────────────────────────────────


_ALL_GREEN = {
    "calendar_density_score": 0.10,
    "after_hours_activity_index": 0.05,
    "context_switch_count": 0.10,
    "sprint_health_index": 0.90,
}

_ALL_RED = {
    "calendar_density_score": 0.90,
    "after_hours_activity_index": 0.80,
    "context_switch_count": 0.80,
    "sprint_health_index": 0.20,
}


# ── Return type ───────────────────────────────────────────────────────────────


def test_returns_list() -> None:
    result = suggest_interventions(_ALL_GREEN)
    assert isinstance(result, list)


def test_returns_intervention_instances() -> None:
    result = suggest_interventions(_ALL_RED)
    for item in result:
        assert isinstance(item, Intervention)


# ── Green features → no interventions ────────────────────────────────────────


def test_green_features_produce_no_interventions() -> None:
    result = suggest_interventions(_ALL_GREEN)
    assert result == []


# ── Individual threshold triggers ────────────────────────────────────────────


def test_high_calendar_density_triggers_meeting_free_friday() -> None:
    features = {**_ALL_GREEN, "calendar_density_score": 0.70}
    ids = [i.id for i in suggest_interventions(features)]
    assert "meeting_free_friday" in ids


def test_high_after_hours_triggers_async_first_week() -> None:
    features = {**_ALL_GREEN, "after_hours_activity_index": 0.65}
    ids = [i.id for i in suggest_interventions(features)]
    assert "async_first_week" in ids


def test_low_sprint_health_triggers_load_redistribution() -> None:
    features = {**_ALL_GREEN, "sprint_health_index": 0.40}
    ids = [i.id for i in suggest_interventions(features)]
    assert "load_redistribution" in ids


def test_high_context_switch_triggers_focus_blocks() -> None:
    features = {**_ALL_GREEN, "context_switch_count": 0.65}
    ids = [i.id for i in suggest_interventions(features)]
    assert "focus_blocks" in ids


def test_all_red_features_trigger_all_interventions() -> None:
    ids = {i.id for i in suggest_interventions(_ALL_RED)}
    assert ids == {"meeting_free_friday", "async_first_week", "load_redistribution", "focus_blocks"}


# ── Boundary conditions ───────────────────────────────────────────────────────


def test_calendar_density_at_exact_threshold() -> None:
    features = {**_ALL_GREEN, "calendar_density_score": 0.65}
    ids = [i.id for i in suggest_interventions(features)]
    assert "meeting_free_friday" in ids


def test_calendar_density_just_below_threshold() -> None:
    features = {**_ALL_GREEN, "calendar_density_score": 0.64}
    ids = [i.id for i in suggest_interventions(features)]
    assert "meeting_free_friday" not in ids


def test_sprint_health_at_exact_threshold() -> None:
    features = {**_ALL_GREEN, "sprint_health_index": 0.50}
    ids = [i.id for i in suggest_interventions(features)]
    assert "load_redistribution" in ids


def test_sprint_health_just_above_threshold() -> None:
    features = {**_ALL_GREEN, "sprint_health_index": 0.51}
    ids = [i.id for i in suggest_interventions(features)]
    assert "load_redistribution" not in ids


# ── Missing features ──────────────────────────────────────────────────────────


def test_empty_features_dict_returns_no_interventions() -> None:
    result = suggest_interventions({})
    assert result == []


# ── Intervention fields ───────────────────────────────────────────────────────


def test_intervention_has_non_empty_title() -> None:
    interventions = suggest_interventions(_ALL_RED)
    for i in interventions:
        assert len(i.title) > 0


def test_intervention_has_non_empty_description() -> None:
    interventions = suggest_interventions(_ALL_RED)
    for i in interventions:
        assert len(i.description) > 0


def test_intervention_ids_are_unique() -> None:
    interventions = suggest_interventions(_ALL_RED)
    ids = [i.id for i in interventions]
    assert len(ids) == len(set(ids))
