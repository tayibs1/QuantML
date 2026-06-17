"""Prometheus /metrics endpoint + request-tracing middleware."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from main import app
from observability import render


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_metrics_endpoint_exposition_format(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "quantml_build_info" in r.text
    assert "quantml_requests_total" in r.text


def test_requests_are_counted(client):
    client.get("/api/health")
    body = client.get("/metrics").text
    # the health route now shows up in the request counters and latency summary
    assert "/api/health" in body
    assert "quantml_request_duration_seconds_count" in body


def test_response_carries_a_trace_id(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Request-ID")


def test_render_always_emits_build_info_and_trailing_newline():
    out = render()
    assert "quantml_build_info" in out
    assert out.endswith("\n")
