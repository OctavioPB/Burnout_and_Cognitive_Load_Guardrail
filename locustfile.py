"""Locust load test for the inference API.

Simulates realistic traffic to POST /predict at 50 RPS and measures p99
latency.  The acceptance criterion is p99 < 200ms.

Usage
-----
    # Start the inference API first:
    uvicorn ml.inference.main:app --port 8001

    # Then run Locust:
    locust -f locustfile.py --host http://localhost:8001 --headless \
           --users 50 --spawn-rate 10 --run-time 60s

    # Or open the Locust web UI:
    locust -f locustfile.py --host http://localhost:8001
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task

# ── Synthetic payloads ────────────────────────────────────────────────────────


def _random_features() -> dict[str, float]:
    return {
        "calendar_density_score": round(random.uniform(0.0, 1.0), 3),
        "after_hours_activity_index": round(random.uniform(0.0, 1.0), 3),
        "context_switch_count": round(random.uniform(0.0, 1.0), 3),
        "sprint_health_index": round(random.uniform(0.0, 1.0), 3),
    }


def _random_history(n: int = 13) -> list[dict[str, float]]:
    return [_random_features() for _ in range(n)]


# ── User behaviors ────────────────────────────────────────────────────────────


class InferenceUser(HttpUser):
    """Simulates a backend service polling the inference API for predictions.

    Task weights reflect expected production traffic split:
    - 70% cold-start (no history): new teams or teams with sparse data
    - 20% warm-start (full 13-day history): established teams
    - 10% health checks: monitoring/alerting systems
    """

    wait_time = between(0.01, 0.05)  # 10–50ms between requests → ~50 RPS per user

    @task(7)
    def predict_cold_start(self) -> None:
        """POST /predict without history (cold-start path)."""
        payload = {
            "team_id": f"T-{random.randint(1, 200)}",
            "workspace_id": "W-load-test",
            "date_utc": "2026-05-08",
            **_random_features(),
        }
        self.client.post("/predict", json=payload, name="/predict [cold]")

    @task(2)
    def predict_warm_start(self) -> None:
        """POST /predict with 13-day history (warm-start / LSTM path)."""
        payload = {
            "team_id": f"T-{random.randint(1, 200)}",
            "workspace_id": "W-load-test",
            "date_utc": "2026-05-08",
            **_random_features(),
            "history": _random_history(13),
        }
        self.client.post("/predict", json=payload, name="/predict [warm]")

    @task(1)
    def health_check(self) -> None:
        """GET /health — monitoring probe."""
        self.client.get("/health", name="/health")
