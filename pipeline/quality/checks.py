"""Data quality checks for the features.team_daily batch.

Implements three categories of checks (mirroring Great Expectations concepts):
  1. Null-rate checks  — columns that must not exceed a missing-value threshold.
  2. Range checks      — numeric columns that must stay within [0.0, 1.0].
  3. Schema-drift check — expected columns must all be present.

Each check returns a QualityCheckResult.  The caller decides whether to fail the
DAG or emit a warning based on the list of results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_MAX_NULL_RATE: float = 0.20  # up to 20 % nulls allowed per feature column

# Columns that must be in [0.0, 1.0] when non-null
_BOUNDED_COLUMNS: frozenset[str] = frozenset(
    {
        "calendar_density_score",
        "after_hours_activity_index",
        "context_switch_count",
        "sprint_health_index",
    }
)

_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "team_id",
        "workspace_id",
        "date_utc",
        "calendar_density_score",
        "after_hours_activity_index",
        "context_switch_count",
    }
)


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class QualityCheckResult:
    check_name: str
    passed: bool
    message: str
    metric: float | None = field(default=None)


# ── Check implementations ─────────────────────────────────────────────────────


def _check_non_empty(records: list[dict]) -> QualityCheckResult:
    passed = len(records) > 0
    return QualityCheckResult(
        check_name="non_empty_batch",
        passed=passed,
        message=f"Batch contains {len(records)} record(s)",
    )


def _check_null_rate(records: list[dict], column: str) -> QualityCheckResult:
    total = len(records)
    null_count = sum(1 for r in records if r.get(column) is None)
    rate = null_count / total if total > 0 else 0.0
    passed = rate <= _MAX_NULL_RATE
    return QualityCheckResult(
        check_name=f"null_rate__{column}",
        passed=passed,
        message=(
            f"{column}: null_rate={rate:.1%} "
            f"({'OK' if passed else f'EXCEEDS threshold {_MAX_NULL_RATE:.0%}'})"
        ),
        metric=rate,
    )


def _check_range(records: list[dict], column: str) -> QualityCheckResult:
    values = [r[column] for r in records if r.get(column) is not None]
    if not values:
        return QualityCheckResult(
            check_name=f"range__{column}",
            passed=True,
            message=f"{column}: no non-null values to check",
        )
    out_of_range = [v for v in values if not (0.0 <= v <= 1.0)]
    passed = len(out_of_range) == 0
    return QualityCheckResult(
        check_name=f"range__{column}",
        passed=passed,
        message=(
            f"{column}: all {len(values)} values in [0,1]"
            if passed
            else f"{column}: {len(out_of_range)} value(s) outside [0,1] — "
            f"min={min(out_of_range):.4f}, max={max(out_of_range):.4f}"
        ),
        metric=float(len(out_of_range)),
    )


def _check_schema_drift(records: list[dict]) -> QualityCheckResult:
    if not records:
        return QualityCheckResult(
            check_name="schema_drift",
            passed=True,
            message="No records to inspect",
        )
    present = set(records[0].keys())
    missing = _REQUIRED_COLUMNS - present
    passed = len(missing) == 0
    return QualityCheckResult(
        check_name="schema_drift",
        passed=passed,
        message=(
            "Schema matches expected columns"
            if passed
            else f"Missing columns: {sorted(missing)}"
        ),
    )


# ── Public entry point ────────────────────────────────────────────────────────


def validate_team_daily_batch(records: list[dict]) -> list[QualityCheckResult]:
    """Run all quality checks on a batch of feature dicts.

    Args:
        records: List of dicts keyed by TeamDailyFeature column names.

    Returns:
        List of QualityCheckResult — one entry per individual check.
        Callers should inspect the ``passed`` field of each result.
    """
    results: list[QualityCheckResult] = []

    non_empty = _check_non_empty(records)
    results.append(non_empty)
    if not non_empty.passed:
        return results  # no point running further checks on empty batch

    results.append(_check_schema_drift(records))

    for col in sorted(_BOUNDED_COLUMNS):
        results.append(_check_null_rate(records, col))
        results.append(_check_range(records, col))

    failed = [r for r in results if not r.passed]
    if failed:
        logger.warning(
            "%d quality check(s) failed: %s",
            len(failed),
            [r.check_name for r in failed],
        )

    return results
