"""Unit tests for ml.inference.alert_engine — AlertEngine."""

from __future__ import annotations

import pytest

from ml.inference.alert_engine import Alert, AlertEngine
from ml.inference.interventions import Intervention


# ── Fixtures ──────────────────────────────────────────────────────────────────


_RED_FEATURES = {
    "calendar_density_score": 0.90,
    "after_hours_activity_index": 0.80,
    "context_switch_count": 0.80,
    "sprint_health_index": 0.20,
}

_GREEN_FEATURES = {
    "calendar_density_score": 0.10,
    "after_hours_activity_index": 0.05,
    "context_switch_count": 0.10,
    "sprint_health_index": 0.90,
}


def _engine(threshold: int = 3) -> AlertEngine:
    return AlertEngine(threshold=threshold)


def _red(engine: AlertEngine, team: str = "T-1", day: str = "2024-01-01") -> Alert | None:
    return engine.process(team, "W-1", day, "red", _RED_FEATURES)


def _green(engine: AlertEngine, team: str = "T-1", day: str = "2024-01-01") -> None:
    engine.process(team, "W-1", day, "green", _GREEN_FEATURES)


def _yellow(engine: AlertEngine, team: str = "T-1", day: str = "2024-01-01") -> None:
    engine.process(team, "W-1", day, "yellow", _GREEN_FEATURES)


# ── Constructor validation ────────────────────────────────────────────────────


def test_threshold_zero_raises() -> None:
    with pytest.raises(ValueError):
        AlertEngine(threshold=0)


def test_threshold_negative_raises() -> None:
    with pytest.raises(ValueError):
        AlertEngine(threshold=-1)


def test_threshold_one_is_valid() -> None:
    engine = AlertEngine(threshold=1)
    assert engine is not None


# ── Streak counting ───────────────────────────────────────────────────────────


def test_initial_streak_is_zero() -> None:
    engine = _engine()
    assert engine.streak("T-1") == 0


def test_red_day_increments_streak() -> None:
    engine = _engine()
    _red(engine)
    assert engine.streak("T-1") == 1


def test_two_red_days_streak_is_two() -> None:
    engine = _engine()
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    assert engine.streak("T-1") == 2


def test_green_day_resets_streak() -> None:
    engine = _engine()
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    _green(engine, day="2024-01-03")
    assert engine.streak("T-1") == 0


def test_yellow_day_resets_streak() -> None:
    engine = _engine()
    _red(engine, day="2024-01-01")
    _yellow(engine, day="2024-01-02")
    assert engine.streak("T-1") == 0


def test_non_red_does_not_return_alert() -> None:
    engine = _engine()
    result = engine.process("T-1", "W-1", "2024-01-01", "green", _GREEN_FEATURES)
    assert result is None


# ── Alert firing ─────────────────────────────────────────────────────────────


def test_alert_not_fired_before_threshold() -> None:
    engine = _engine(threshold=3)
    _red(engine, day="2024-01-01")
    result = _red(engine, day="2024-01-02")
    assert result is None


def test_alert_fires_at_exactly_threshold() -> None:
    engine = _engine(threshold=3)
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    alert = _red(engine, day="2024-01-03")
    assert isinstance(alert, Alert)


def test_alert_fires_with_threshold_one() -> None:
    engine = _engine(threshold=1)
    alert = _red(engine, day="2024-01-01")
    assert isinstance(alert, Alert)


def test_alert_contains_correct_team_id() -> None:
    engine = _engine(threshold=1)
    alert = _red(engine, team="T-42")
    assert alert is not None
    assert alert.team_id == "T-42"


def test_alert_contains_correct_workspace_id() -> None:
    engine = _engine(threshold=1)
    alert = engine.process("T-1", "W-99", "2024-01-01", "red", _RED_FEATURES)
    assert alert is not None
    assert alert.workspace_id == "W-99"


def test_alert_contains_correct_trigger_date() -> None:
    engine = _engine(threshold=1)
    alert = _red(engine, day="2024-06-15")
    assert alert is not None
    assert alert.trigger_date == "2024-06-15"


def test_alert_consecutive_red_days_matches_threshold() -> None:
    engine = _engine(threshold=3)
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    alert = _red(engine, day="2024-01-03")
    assert alert is not None
    assert alert.consecutive_red_days == 3


def test_alert_interventions_is_list() -> None:
    engine = _engine(threshold=1)
    alert = _red(engine)
    assert alert is not None
    assert isinstance(alert.interventions, list)


def test_alert_interventions_contain_intervention_instances() -> None:
    engine = _engine(threshold=1)
    alert = engine.process("T-1", "W-1", "2024-01-01", "red", _RED_FEATURES)
    assert alert is not None
    for item in alert.interventions:
        assert isinstance(item, Intervention)


def test_alert_features_match_input() -> None:
    engine = _engine(threshold=1)
    alert = engine.process("T-1", "W-1", "2024-01-01", "red", _RED_FEATURES)
    assert alert is not None
    assert alert.features == _RED_FEATURES


# ── Counter reset after alert ─────────────────────────────────────────────────


def test_streak_resets_to_zero_after_alert() -> None:
    engine = _engine(threshold=3)
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    _red(engine, day="2024-01-03")  # fires alert
    assert engine.streak("T-1") == 0


def test_no_alert_on_day_after_reset() -> None:
    """After an alert fires and resets the counter, the next red day alone
    should not trigger another alert (needs a fresh full streak)."""
    engine = _engine(threshold=3)
    for day in ["2024-01-01", "2024-01-02", "2024-01-03"]:
        _red(engine, day=day)  # fires alert on day 3
    result = _red(engine, day="2024-01-04")
    assert result is None


def test_second_alert_fires_after_fresh_streak() -> None:
    engine = _engine(threshold=2)
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")  # first alert
    result1 = _red(engine, day="2024-01-03")
    result2 = _red(engine, day="2024-01-04")  # second alert
    assert result1 is None
    assert isinstance(result2, Alert)


# ── Isolation between teams ───────────────────────────────────────────────────


def test_streaks_are_independent_per_team() -> None:
    engine = _engine(threshold=3)
    _red(engine, team="T-A", day="2024-01-01")
    _red(engine, team="T-A", day="2024-01-02")
    _red(engine, team="T-B", day="2024-01-01")
    assert engine.streak("T-A") == 2
    assert engine.streak("T-B") == 1


def test_alert_fires_for_one_team_not_the_other() -> None:
    engine = _engine(threshold=2)
    _red(engine, team="T-A", day="2024-01-01")
    alert = _red(engine, team="T-A", day="2024-01-02")
    no_alert = _red(engine, team="T-B", day="2024-01-01")
    assert isinstance(alert, Alert)
    assert no_alert is None


# ── Manual reset ──────────────────────────────────────────────────────────────


def test_reset_clears_team_streak() -> None:
    engine = _engine()
    _red(engine, day="2024-01-01")
    _red(engine, day="2024-01-02")
    engine.reset("T-1")
    assert engine.streak("T-1") == 0


def test_reset_all_clears_all_teams() -> None:
    engine = _engine()
    _red(engine, team="T-A")
    _red(engine, team="T-B")
    engine.reset_all()
    assert engine.streak("T-A") == 0
    assert engine.streak("T-B") == 0


def test_reset_does_not_affect_other_teams() -> None:
    engine = _engine()
    _red(engine, team="T-A")
    _red(engine, team="T-B")
    engine.reset("T-A")
    assert engine.streak("T-B") == 1


# ── External state store ──────────────────────────────────────────────────────


def test_external_store_is_used() -> None:
    store: dict[str, int] = {}
    engine = AlertEngine(threshold=3, state_store=store)
    _red(engine)
    assert store.get("T-1") == 1


def test_prepopulated_store_is_respected() -> None:
    store: dict[str, int] = {"T-1": 2}
    engine = AlertEngine(threshold=3, state_store=store)
    alert = _red(engine, day="2024-01-03")  # streak becomes 3 → fires
    assert isinstance(alert, Alert)
    assert alert.consecutive_red_days == 3
