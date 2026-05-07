"""Unit tests for pipeline data quality checks."""

from __future__ import annotations

from pipeline.quality.checks import (
    _MAX_NULL_RATE,
    _REQUIRED_COLUMNS,
    validate_team_daily_batch,
)


def _base_record(**kwargs: object) -> dict:
    rec = {
        "team_id": "T001",
        "workspace_id": "W001",
        "date_utc": "2024-01-15",
        "calendar_density_score": 0.25,
        "after_hours_activity_index": 0.1,
        "context_switch_count": 0.3,
        "sprint_health_index": 0.75,
        "team_size": 5,
    }
    rec.update(kwargs)
    return rec


def _passed(results, check_prefix: str) -> bool:
    return all(r.passed for r in results if r.check_name.startswith(check_prefix))


# ── Empty batch ───────────────────────────────────────────────────────────────


def test_empty_batch_fails_non_empty_check() -> None:
    results = validate_team_daily_batch([])
    non_empty = next(r for r in results if r.check_name == "non_empty_batch")
    assert not non_empty.passed


def test_empty_batch_returns_only_non_empty_check() -> None:
    # No downstream checks run when batch is empty
    results = validate_team_daily_batch([])
    assert len(results) == 1


# ── Schema drift ──────────────────────────────────────────────────────────────


def test_schema_drift_passes_on_valid_records() -> None:
    results = validate_team_daily_batch([_base_record()])
    schema = next(r for r in results if r.check_name == "schema_drift")
    assert schema.passed


def test_schema_drift_fails_on_missing_required_column() -> None:
    record = _base_record()
    del record["team_id"]
    results = validate_team_daily_batch([record])
    schema = next(r for r in results if r.check_name == "schema_drift")
    assert not schema.passed
    assert "team_id" in schema.message


def test_schema_drift_all_required_columns_tested() -> None:
    for col in _REQUIRED_COLUMNS:
        record = _base_record()
        del record[col]
        results = validate_team_daily_batch([record])
        schema_check = next(r for r in results if r.check_name == "schema_drift")
        assert not schema_check.passed, f"Expected failure for missing column {col}"


# ── Null-rate checks ──────────────────────────────────────────────────────────


def test_null_rate_passes_when_all_non_null() -> None:
    records = [_base_record() for _ in range(10)]
    results = validate_team_daily_batch(records)
    assert _passed(results, "null_rate__")


def test_null_rate_passes_at_exactly_threshold() -> None:
    n = 10
    threshold_count = int(n * _MAX_NULL_RATE)
    records = [_base_record() for _ in range(n - threshold_count)]
    records += [_base_record(calendar_density_score=None) for _ in range(threshold_count)]
    results = validate_team_daily_batch(records)
    cds_null = next(r for r in results if r.check_name == "null_rate__calendar_density_score")
    assert cds_null.passed


def test_null_rate_fails_when_too_many_nulls() -> None:
    records = [_base_record(after_hours_activity_index=None) for _ in range(10)]
    results = validate_team_daily_batch(records)
    ahai_null = next(r for r in results if r.check_name == "null_rate__after_hours_activity_index")
    assert not ahai_null.passed
    assert ahai_null.metric == 1.0


# ── Range checks ─────────────────────────────────────────────────────────────


def test_range_passes_for_valid_values() -> None:
    records = [_base_record()]
    results = validate_team_daily_batch(records)
    assert _passed(results, "range__")


def test_range_passes_at_boundaries() -> None:
    records = [
        _base_record(
            calendar_density_score=0.0,
            after_hours_activity_index=1.0,
            context_switch_count=0.0,
            sprint_health_index=1.0,
        )
    ]
    results = validate_team_daily_batch(records)
    assert _passed(results, "range__")


def test_range_fails_for_value_above_one() -> None:
    records = [_base_record(calendar_density_score=1.1)]
    results = validate_team_daily_batch(records)
    cds_range = next(r for r in results if r.check_name == "range__calendar_density_score")
    assert not cds_range.passed


def test_range_fails_for_negative_value() -> None:
    records = [_base_record(context_switch_count=-0.01)]
    results = validate_team_daily_batch(records)
    csc_range = next(r for r in results if r.check_name == "range__context_switch_count")
    assert not csc_range.passed


def test_range_skips_null_values() -> None:
    # sprint_health_index is allowed to be None (insufficient data)
    records = [_base_record(sprint_health_index=None)]
    results = validate_team_daily_batch(records)
    shi_range = next(r for r in results if r.check_name == "range__sprint_health_index")
    assert shi_range.passed


# ── Full happy path ───────────────────────────────────────────────────────────


def test_all_checks_pass_for_clean_batch() -> None:
    records = [_base_record() for _ in range(5)]
    results = validate_team_daily_batch(records)
    failed = [r for r in results if not r.passed]
    assert failed == [], f"Unexpected failures: {[r.check_name for r in failed]}"
