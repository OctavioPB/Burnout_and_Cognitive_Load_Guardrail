"""Locust load test — Burnout Guardrail Backend API.

Simulates two user populations:
  - HRAdminUser  : reads summary, teams, alerts, audit log; applies/dismisses interventions
  - ViewerUser   : reads summary, teams, and alert feed only

Target thresholds (from PLAN.md):
  200 RPS sustained, p99 < 300ms

Run locally:
  locust -f tests/load/locustfile.py --host http://localhost:8000 \\
         --users 50 --spawn-rate 5 --run-time 60s --headless

CI/CD headless smoke test (10 users, 30s):
  locust -f tests/load/locustfile.py --host http://localhost:8000 \\
         --users 10 --spawn-rate 2 --run-time 30s --headless \\
         --exit-code-on-error 1
"""

from __future__ import annotations

from locust import HttpUser, between, task

# ── Auth header factories ──────────────────────────────────────────────────────

_HR_HEADERS = {
    "X-User-Id":   "load-hr-01",
    "X-User-Name": "Load Test HR",
    "X-User-Role": "hr_admin",
}

_VIEWER_HEADERS = {
    "X-User-Id":   "load-viewer-01",
    "X-User-Name": "Load Test Viewer",
    "X-User-Role": "viewer",
}

_TEAM_MGR_HEADERS = {
    "X-User-Id":     "load-mgr-01",
    "X-User-Name":   "Load Test Manager",
    "X-User-Role":   "team_manager",
    "X-User-Team-Id": "T-01",   # Frontier Engineering — first mock team
}

# ── Helper: resolve a real team_id from the teams list ────────────────────────

_CACHED_TEAM_IDS: list[str] = []


def _get_team_ids(client) -> list[str]:  # type: ignore[no-untyped-def]
    global _CACHED_TEAM_IDS
    if not _CACHED_TEAM_IDS:
        r = client.get("/dashboard/teams", name="/dashboard/teams [setup]")
        if r.status_code == 200:
            _CACHED_TEAM_IDS = [t["team_id"] for t in r.json()]
    return _CACHED_TEAM_IDS


# ── User classes ───────────────────────────────────────────────────────────────

class HRAdminUser(HttpUser):
    """HR Admin — full read/write access.  Models the most privileged user type."""

    wait_time = between(0.5, 2.0)
    weight = 3  # 3× more HR admins than viewers in the mix

    def on_start(self) -> None:
        self._team_ids = _get_team_ids(self.client)

    # ── Read-heavy tasks (high weight = called more often) ────────────────────

    @task(10)
    def dashboard_summary(self) -> None:
        self.client.get("/dashboard/summary", headers=_HR_HEADERS,
                        name="/dashboard/summary")

    @task(8)
    def dashboard_teams(self) -> None:
        self.client.get("/dashboard/teams", headers=_HR_HEADERS,
                        name="/dashboard/teams")

    @task(6)
    def team_history(self) -> None:
        if not self._team_ids:
            return
        import random
        tid = random.choice(self._team_ids)
        self.client.get(f"/teams/{tid}/history", headers=_HR_HEADERS,
                        name="/teams/{team_id}/history")

    @task(5)
    def alerts(self) -> None:
        self.client.get("/alerts", headers=_HR_HEADERS, name="/alerts")

    @task(3)
    def alerts_filtered(self) -> None:
        self.client.get("/alerts?department=Engineering", headers=_HR_HEADERS,
                        name="/alerts?department=*")

    @task(4)
    def team_interventions(self) -> None:
        if not self._team_ids:
            return
        import random
        tid = random.choice(self._team_ids)
        self.client.get(f"/interventions/{tid}", headers=_HR_HEADERS,
                        name="/interventions/{team_id}")

    @task(2)
    def audit_log(self) -> None:
        self.client.get("/audit?limit=50", headers=_HR_HEADERS,
                        name="/audit")

    # ── Write tasks (low weight — interventions are rare real-world events) ───

    @task(1)
    def apply_focus_blocks(self) -> None:
        if not self._team_ids:
            return
        import random
        tid = random.choice(self._team_ids)
        self.client.post(
            f"/interventions/{tid}/apply",
            json={"intervention_id": "focus_blocks"},
            headers=_HR_HEADERS,
            name="/interventions/{team_id}/apply",
        )

    @task(1)
    def dismiss_intervention(self) -> None:
        if not self._team_ids:
            return
        import random
        tid = random.choice(self._team_ids)
        self.client.post(
            f"/interventions/{tid}/dismiss",
            json={"intervention_id": "meeting_free_friday"},
            headers=_HR_HEADERS,
            name="/interventions/{team_id}/dismiss",
        )

    @task(1)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")


class ViewerUser(HttpUser):
    """Read-only user — analyst / exec viewing the dashboard."""

    wait_time = between(1.0, 4.0)
    weight = 7  # majority of traffic is read-only viewers

    def on_start(self) -> None:
        self._team_ids = _get_team_ids(self.client)

    @task(10)
    def dashboard_summary(self) -> None:
        self.client.get("/dashboard/summary", headers=_VIEWER_HEADERS,
                        name="/dashboard/summary")

    @task(8)
    def dashboard_teams(self) -> None:
        self.client.get("/dashboard/teams", headers=_VIEWER_HEADERS,
                        name="/dashboard/teams")

    @task(5)
    def team_history(self) -> None:
        if not self._team_ids:
            return
        import random
        tid = random.choice(self._team_ids)
        self.client.get(f"/teams/{tid}/history", headers=_VIEWER_HEADERS,
                        name="/teams/{team_id}/history")

    @task(4)
    def alerts(self) -> None:
        self.client.get("/alerts", headers=_VIEWER_HEADERS, name="/alerts")

    @task(1)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")


class TeamManagerUser(HttpUser):
    """Team Manager — can only see their own team."""

    wait_time = between(2.0, 5.0)
    weight = 2

    @task(5)
    def own_team_history(self) -> None:
        self.client.get("/teams/T-01/history", headers=_TEAM_MGR_HEADERS,
                        name="/teams/{team_id}/history [manager]")

    @task(3)
    def own_team_interventions(self) -> None:
        self.client.get("/interventions/T-01", headers=_TEAM_MGR_HEADERS,
                        name="/interventions/{team_id} [manager]")

    @task(1)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")
