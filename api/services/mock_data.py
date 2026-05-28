"""Deterministic seeded mock data for staging (10+ team units, 30-day history).

All data is generated once at module import and held in module-level constants.
The generator uses a simple hash of team_id as its seed so the output is stable
across restarts — the same team always has the same trajectory.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import date, timedelta

from api.schemas.dashboard import (
    AlertRecord,
    DashboardSummary,
    DayPoint,
    DeptSummary,
    FeatureScores,
    InterventionItem,
    OrgHistory,
    OrgTrendPoint,
    TeamCard,
    TeamHistory,
    TeamTrendSeries,
)

# ── Team registry ─────────────────────────────────────────────────────────────

_TEAMS: list[dict[str, str]] = [
    {"team_id": "T-01", "team_name": "Frontend Engineering", "department": "Engineering"},
    {"team_id": "T-02", "team_name": "Backend Engineering",  "department": "Engineering"},
    {"team_id": "T-03", "team_name": "Infrastructure",       "department": "Engineering"},
    {"team_id": "T-04", "team_name": "Mobile Engineering",   "department": "Engineering"},
    {"team_id": "T-05", "team_name": "Core Product",         "department": "Product"},
    {"team_id": "T-06", "team_name": "Growth Product",       "department": "Product"},
    {"team_id": "T-07", "team_name": "Platform Product",     "department": "Product"},
    {"team_id": "T-08", "team_name": "UX Design",            "department": "Design"},
    {"team_id": "T-09", "team_name": "Brand Design",         "department": "Design"},
    {"team_id": "T-10", "team_name": "Analytics",            "department": "Data"},
    {"team_id": "T-11", "team_name": "ML Engineering",       "department": "Data"},
    {"team_id": "T-12", "team_name": "Business Intelligence", "department": "Data"},
]

_WORKSPACE_ID = "W-main"

# ── Seed configuration ────────────────────────────────────────────────────────

class SeedConfig:
    """Controls the team roster and stress distribution used by _DataStore."""

    def __init__(
        self,
        teams: list[dict[str, str]] | None = None,
        stress_profile: str = "mixed",
        history_days: int = 30,
    ) -> None:
        self.teams = teams if teams is not None else list(_TEAMS)
        self.stress_profile = stress_profile
        self.history_days = history_days


_STRESS_RANGE: dict[str, tuple[float, float]] = {
    "low":   (0.05, 0.40),
    "mixed": (0.00, 1.00),
    "high":  (0.55, 0.95),
}

# ── Seeded RNG ────────────────────────────────────────────────────────────────

def _rng(team_id: str) -> random.Random:
    seed = int(hashlib.md5(team_id.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


# ── Feature + AFS generation ──────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _afs_from_features(cds: float, ahai: float, csc: float, shi: float) -> float:
    """Replicate the AFS formula used in ml.training.features."""
    raw = (0.30 * cds + 0.30 * ahai + 0.20 * csc + 0.20 * (1.0 - shi)) * 100.0
    return round(float(_clamp(raw, 0.0, 100.0)), 1)


def _zone(afs: float) -> tuple[str, int]:
    if afs <= 39:
        return "green", 0
    if afs <= 69:
        return "yellow", 1
    return "red", 2


# ── 30-day history builder ────────────────────────────────────────────────────

def _build_history(
    team_id: str,
    days: int = 30,
    base_range: tuple[float, float] = (0.0, 1.0),
) -> list[DayPoint]:
    rng = _rng(team_id)
    base = rng.uniform(*base_range)
    today = date.today()

    points: list[DayPoint] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        # Add daily noise around the base
        noise = rng.gauss(0, 0.07)
        # Slow drift toward stress peak mid-history then recovery
        cycle = 0.15 * math.sin(math.pi * (days - offset) / days)
        cds   = _clamp(base + noise + cycle + rng.gauss(0, 0.05))
        ahai  = _clamp(base * 0.9 + noise + rng.gauss(0, 0.06))
        csc   = _clamp(base * 0.8 + noise + rng.gauss(0, 0.07))
        shi   = _clamp(1.0 - base * 0.85 + rng.gauss(0, 0.06))
        afs   = _afs_from_features(cds, ahai, csc, shi)
        zone, _ = _zone(afs)
        points.append(DayPoint(
            date=day.isoformat(),
            afs=afs,
            zone=zone,
            calendar_density_score=round(cds, 3),
            after_hours_activity_index=round(ahai, 3),
            context_switch_count=round(csc, 3),
            sprint_health_index=round(shi, 3),
        ))
    return points


def _latest_features(history: list[DayPoint]) -> FeatureScores:
    last = history[-1]
    return FeatureScores(
        calendar_density_score=last.calendar_density_score,
        after_hours_activity_index=last.after_hours_activity_index,
        context_switch_count=last.context_switch_count,
        sprint_health_index=last.sprint_health_index,
    )


# ── Intervention rule evaluation ──────────────────────────────────────────────

_INTERVENTION_RULES: list[tuple[str, str, str, float, str]] = [
    ("calendar_density_score",      "ge", "meeting_free_friday",  0.65, "Meeting-Free Friday"),
    ("after_hours_activity_index",  "ge", "async_first_week",     0.60, "Async-First Week"),
    ("sprint_health_index",         "le", "load_redistribution",  0.50, "Load Redistribution"),
    ("context_switch_count",        "ge", "focus_blocks",         0.60, "Deep Work Blocks"),
]

_INTERVENTION_DESC: dict[str, str] = {
    "meeting_free_friday": "Block all recurring meetings on Fridays for 4 weeks.",
    "async_first_week":    "Disable Slack notifications after 18:00 for one week.",
    "load_redistribution": "Schedule a capacity review to reduce sprint commitments by ≥ 20%.",
    "focus_blocks":        "Reserve 2-hour focus blocks three mornings per week.",
}


def _suggest(features: FeatureScores) -> list[InterventionItem]:
    f = features.model_dump()
    result = []
    for feat, op, iid, thresh, title in _INTERVENTION_RULES:
        val = f.get(feat)
        if val is None:
            continue
        triggered = (op == "ge" and val >= thresh) or (op == "le" and val <= thresh)
        if triggered:
            result.append(
                InterventionItem(id=iid, title=title, description=_INTERVENTION_DESC[iid])
            )
    return result


# ── Alert generation ──────────────────────────────────────────────────────────

def _build_alerts(team_id: str, team_name: str, department: str,
                  history: list[DayPoint]) -> list[AlertRecord]:
    alerts: list[AlertRecord] = []
    streak = 0
    for _, pt in enumerate(history):
        if pt.zone == "red":
            streak += 1
            if streak >= 3:
                features = FeatureScores(
                    calendar_density_score=pt.calendar_density_score,
                    after_hours_activity_index=pt.after_hours_activity_index,
                    context_switch_count=pt.context_switch_count,
                    sprint_health_index=pt.sprint_health_index,
                )
                alerts.append(AlertRecord(
                    alert_id=f"{team_id}-{pt.date}",
                    team_id=team_id,
                    team_name=team_name,
                    department=department,
                    workspace_id=_WORKSPACE_ID,
                    trigger_date=pt.date,
                    consecutive_red_days=streak,
                    interventions=_suggest(features),
                ))
                streak = 0  # reset after alert fires
        else:
            streak = 0
    return alerts


# ── Module-level data store (built once) ─────────────────────────────────────

class _DataStore:
    def __init__(self, config: SeedConfig | None = None) -> None:
        cfg = config if config is not None else SeedConfig()
        base_range = _STRESS_RANGE.get(cfg.stress_profile, (0.0, 1.0))

        self._histories: dict[str, list[DayPoint]] = {}
        self._team_cards: list[TeamCard] = []
        self._alerts: list[AlertRecord] = []

        for t in cfg.teams:
            tid, tname, dept = t["team_id"], t["team_name"], t["department"]
            history = _build_history(tid, days=cfg.history_days, base_range=base_range)
            self._histories[tid] = history

            last = history[-1]
            feats = _latest_features(history)
            zone, zlabel = _zone(last.afs)
            team_alerts = _build_alerts(tid, tname, dept, history)
            self._alerts.extend(team_alerts)

            self._team_cards.append(TeamCard(
                team_id=tid,
                team_name=tname,
                department=dept,
                zone=zone,
                zone_label=zlabel,
                afs=last.afs,
                features=feats,
                has_active_alert=any(a.trigger_date == last.date for a in team_alerts),
            ))

        self._alerts.sort(key=lambda a: a.trigger_date, reverse=True)

    # ── Accessors ──────────────────────────────────────────────────────────────

    def summary(self) -> DashboardSummary:
        by_dept: dict[str, dict[str, int]] = {}
        green = yellow = red = 0
        for card in self._team_cards:
            if card.zone == "green":
                green += 1
            elif card.zone == "yellow":
                yellow += 1
            else:
                red += 1
            d = by_dept.setdefault(card.department, {"green": 0, "yellow": 0, "red": 0, "total": 0})
            d[card.zone] += 1
            d["total"] += 1

        active_alerts = sum(1 for c in self._team_cards if c.has_active_alert)

        return DashboardSummary(
            total_teams=len(self._team_cards),
            green=green,
            yellow=yellow,
            red=red,
            active_alerts=active_alerts,
            departments=[
                DeptSummary(department=dept, **counts)
                for dept, counts in sorted(by_dept.items())
            ],
        )

    def teams(self, department: str | None = None) -> list[TeamCard]:
        cards = self._team_cards
        if department:
            cards = [c for c in cards if c.department == department]
        return sorted(cards, key=lambda c: c.afs, reverse=True)

    def team_history(self, team_id: str) -> TeamHistory | None:
        meta = next((t for t in _TEAMS if t["team_id"] == team_id), None)
        if meta is None:
            return None
        history = self._histories[team_id]
        last = history[-1]
        feats = _latest_features(history)
        zone, _ = _zone(last.afs)
        return TeamHistory(
            team_id=team_id,
            team_name=meta["team_name"],
            department=meta["department"],
            zone=zone,
            afs=last.afs,
            features=feats,
            history=history,
            interventions=_suggest(feats),
        )

    def org_history(self) -> OrgHistory:
        """Return 30-day AFS time series aggregated at org, dept, and team levels."""
        sample = next(iter(self._histories.values()))
        dates = [pt.date for pt in sample]

        date_org: dict[str, list[float]] = {d: [] for d in dates}
        date_dept: dict[str, dict[str, list[float]]] = {}
        for t in _TEAMS:
            tid, dept = t["team_id"], t["department"]
            if dept not in date_dept:
                date_dept[dept] = {d: [] for d in dates}
            for pt in self._histories[tid]:
                date_org[pt.date].append(pt.afs)
                date_dept[dept][pt.date].append(pt.afs)

        org = [
            OrgTrendPoint(date=d, afs=round(sum(vals) / len(vals), 1))
            for d, vals in sorted(date_org.items()) if vals
        ]
        by_department: dict[str, list[OrgTrendPoint]] = {
            dept: [
                OrgTrendPoint(date=d, afs=round(sum(vals) / len(vals), 1))
                for d, vals in sorted(day_vals.items()) if vals
            ]
            for dept, day_vals in date_dept.items()
        }
        by_team: dict[str, TeamTrendSeries] = {
            t["team_id"]: TeamTrendSeries(
                name=t["team_name"],
                department=t["department"],
                history=[
                    OrgTrendPoint(date=pt.date, afs=pt.afs)
                    for pt in self._histories[t["team_id"]]
                ],
            )
            for t in _TEAMS
        }
        return OrgHistory(org=org, by_department=by_department, by_team=by_team)

    def alerts(self, department: str | None = None, limit: int = 50) -> list[AlertRecord]:
        result = self._alerts
        if department:
            result = [a for a in result if next(
                (t["department"] for t in _TEAMS if t["team_id"] == a.team_id), ""
            ) == department]
        return result[:limit]


class _StoreProxy:
    """Thin proxy that lets callers hold a stable reference to `store` while
    allowing the underlying _DataStore to be swapped out by the admin API."""

    def __init__(self) -> None:
        self._inner: _DataStore = _DataStore()

    def reset(self, config: SeedConfig | None = None) -> None:
        self._inner = _DataStore(config=config)

    def summary(self) -> DashboardSummary:
        return self._inner.summary()

    def teams(self, department: str | None = None) -> list[TeamCard]:
        return self._inner.teams(department=department)

    def team_history(self, team_id: str) -> TeamHistory | None:
        return self._inner.team_history(team_id)

    def org_history(self) -> OrgHistory:
        return self._inner.org_history()

    def alerts(self, department: str | None = None, limit: int = 50) -> list[AlertRecord]:
        return self._inner.alerts(department=department, limit=limit)


store = _StoreProxy()
