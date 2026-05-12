"""Unit tests for the three api/middleware modules.

Tests are kept focused on observable behaviour:
  - SecurityHeadersMiddleware: correct headers are present / absent on responses
  - CorrelationLoggingMiddleware: request ID echoed back; new ID generated when absent
  - PrometheusMiddleware + /metrics endpoint: endpoint reachable and returns text
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

_AUTH = {
    "X-User-Id":   "u-test",
    "X-User-Name": "Test User",
    "X-User-Role": "hr_admin",
}

# ── Security headers ──────────────────────────────────────────────────────────

def test_security_header_hsts() -> None:
    r = client.get("/health")
    assert "strict-transport-security" in r.headers
    assert "max-age=63072000" in r.headers["strict-transport-security"]


def test_security_header_xcto() -> None:
    r = client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"


def test_security_header_xframe() -> None:
    r = client.get("/health")
    assert r.headers.get("x-frame-options") == "DENY"


def test_security_header_referrer_policy() -> None:
    r = client.get("/health")
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_security_header_csp_present() -> None:
    r = client.get("/health")
    assert "content-security-policy" in r.headers


def test_security_header_permissions_policy() -> None:
    r = client.get("/health")
    assert "permissions-policy" in r.headers
    assert "camera=()" in r.headers["permissions-policy"]


def test_security_header_present_on_api_response_too() -> None:
    r = client.get("/dashboard/summary")
    assert r.headers.get("x-content-type-options") == "nosniff"


# ── Correlation logging middleware ────────────────────────────────────────────

def test_request_id_echoed_when_provided() -> None:
    r = client.get("/health", headers={"X-Request-Id": "my-trace-id-123"})
    assert r.headers.get("x-request-id") == "my-trace-id-123"


def test_request_id_generated_when_absent() -> None:
    r = client.get("/health")
    rid = r.headers.get("x-request-id", "")
    assert len(rid) == 36  # UUID4 format: 8-4-4-4-12


def test_different_requests_get_different_request_ids() -> None:
    r1 = client.get("/health")
    r2 = client.get("/health")
    assert r1.headers.get("x-request-id") != r2.headers.get("x-request-id")


def test_request_id_propagated_to_api_response() -> None:
    r = client.get("/dashboard/summary", headers={"X-Request-Id": "trace-abc"})
    assert r.headers.get("x-request-id") == "trace-abc"


# ── Prometheus metrics endpoint ───────────────────────────────────────────────

def test_metrics_endpoint_is_reachable() -> None:
    r = client.get("/metrics")
    assert r.status_code == 200


def test_metrics_endpoint_returns_text_content() -> None:
    r = client.get("/metrics")
    content_type = r.headers.get("content-type", "")
    # Prometheus returns text/plain; charset=utf-8
    assert "text/plain" in content_type or r.status_code == 503  # 503 if prom not installed


def test_metrics_endpoint_contains_http_requests_total() -> None:
    # Trigger a request first so the counter is non-zero
    client.get("/health")
    r = client.get("/metrics")
    if r.status_code == 200:
        assert "http_requests_total" in r.text


def test_metrics_endpoint_contains_latency_histogram() -> None:
    client.get("/dashboard/summary")
    r = client.get("/metrics")
    if r.status_code == 200:
        assert "http_request_duration_seconds" in r.text


def test_metrics_endpoint_not_in_openapi_schema() -> None:
    r = client.get("/openapi.json")
    assert "/metrics" not in r.text
