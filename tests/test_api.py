"""End-to-end API checks through FastAPI's TestClient.

These assert shape and the safety contract, not exact numbers - in CI there are
no data/ artifacts, so every endpoint serves its seeded mock fallback. That's the
whole point of the graceful-degradation design, and it keeps these tests offline.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "QuantML API"


def test_health_reports_execution_safety(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "operational"
    # live trading must read as disabled in the health payload
    assert body["liveTradingEnabled"] is False
    assert body["executionMode"] in {"backtest", "paper", "live"}


def test_monitoring_endpoint_degrades_cleanly(client):
    # Before the pipeline runs (no artifacts in CI), monitoring must 200 with
    # null payloads and an "unknown" status rather than erroring.
    r = client.get("/api/monitoring")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"dataHealth", "drift", "status"}
    assert set(body["status"]) >= {"data", "drift"}


def test_validation_endpoint_degrades_cleanly(client):
    r = client.get("/api/validation")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"rollingWindow", "windowComparison"}


def test_replay_endpoint_shape(client):
    r = client.get("/api/replay")
    assert r.status_code == 200
    scenarios = r.json()["scenarios"]
    assert isinstance(scenarios, list)
    # data/ artifacts are absent in CI, so the list may be empty; when present,
    # each scenario carries the trade, the price path, and the entry/exit markers.
    for sc in scenarios:
        assert {"signal", "ticker", "ret", "drivers", "correct", "series"} <= set(sc)
        assert sc["signal"] in {"BUY", "HOLD", "AVOID"}
        assert isinstance(sc["series"], list) and sc["series"]
        assert 0 <= sc["entryIndex"] < sc["exitIndex"] < len(sc["series"])


def test_signals_shape(client):
    r = client.get("/api/signals")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and rows
    first = rows[0]
    for key in ("ticker", "signal", "confidence", "drivers", "sector"):
        assert key in first
    assert first["signal"] in {"BUY", "HOLD", "AVOID"}


def test_signals_filter(client):
    r = client.get("/api/signals?type=BUY")
    assert r.status_code == 200
    assert all(s["signal"] == "BUY" for s in r.json())


def test_metrics_returns_eight_cards(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200
    cards = r.json()
    assert len(cards) == 8
    assert all("label" in c and "value" in c for c in cards)


def test_equity_series(client):
    r = client.get("/api/equity")
    assert r.status_code == 200
    series = r.json()
    assert series and {"date", "strategy", "benchmark", "drawdown"} <= set(series[0])


def test_models_registry(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    body = r.json()
    assert body["models"] and "featureImportance" in body
    # versioned-champion registry travels with the models payload
    assert "registry" in body and "versions" in body["registry"]


def test_risk_summary_shape(client):
    r = client.get("/api/risk")
    assert r.status_code == 200
    body = r.json()
    for key in ("flags", "budget", "exposureByAsset", "exposureBySector", "positionRules"):
        assert key in body


def test_proposed_orders_never_exceed_caps(client):
    r = client.get("/api/portfolio/proposed-orders")
    assert r.status_code == 200
    summary = r.json()["summary"]
    assert summary["grossExposure"] <= 1.0 + 1e-3   # cap holds modulo 4dp rounding
    assert summary["largestPosition"] <= 0.20 + 1e-3


def test_execution_preview_is_never_live(client):
    r = client.get("/api/execution")
    assert r.status_code == 200
    assert r.json()["liveTradingEnabled"] is False


def test_backtest_post_returns_full_result(client):
    # no artifacts in CI -> service returns its mock-shaped result, still valid
    r = client.post("/api/backtests", json={"rebalance": "Weekly"})
    assert r.status_code == 200
    body = r.json()
    for key in ("source", "equity", "summaryCards", "tradeCount"):
        assert key in body
    assert body["source"] in {"live", "mock"}
