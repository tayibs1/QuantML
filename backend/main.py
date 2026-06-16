"""
QuantML API - the FastAPI backend.

Serves the JSON the Next.js frontend reads, all under /api so the frontend's api
client behaves the same whether it's hitting this backend or its own built-in
mock routes. /api/signals and /api/models go live the moment the ML pipeline has
run (they read artifacts out of data/); until then everything drops back to
seeded mock data, so the API is never down.

The architecture this enforces:
    Signal Engine (ml/)  ->  Portfolio/Risk (portfolio/)  ->  Execution (execution/)
Signal endpoints only read predictions. Turning signals into orders is the risk
layer's job; acting on orders only ever happens inside the execution adapter that
EXECUTION_MODE selects (backtest is built, paper/live are gated off).

Run it from backend/:
    uvicorn main:app --reload --port 8000

Point the frontend at it via frontend/.env.local:
    NEXT_PUBLIC_API_URL=http://localhost:8000
"""
from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

import mock_data as mock
from config import settings
from execution import get_execution_adapter
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from portfolio import propose_orders
from schemas import (
    BacktestRequest,
    Metric,
    MetricPoint,
    RagResponse,
    ResearchRequest,
    Signal,
    Trade,
)
from services import backtest_service, risk_service, store

app = FastAPI(title="QuantML API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# everything lives under /api so swapping in for the Next.js mock routes is clean
api = APIRouter(prefix="/api")


def _read_json(path: Path) -> dict | None:
    """Best-effort read of a pipeline artifact; None if missing or unreadable."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return None


@app.get("/")
def root():
    return {"name": "QuantML API", "version": "0.2.0", "docs": "/docs", "api": "/api"}


# --- health / status ---
@api.get("/health")
def health():
    # fast check: no disk I/O. signals source becomes "unknown" until a real signals call
    # hits /api/signals and populates the cache. this keeps health fast (<1ms).
    return {
        "status": "operational",
        "model": settings.default_model,
        "universe": settings.universe,
        "paperMode": settings.trading_mode == "paper",
        "version": "0.2.0",
        "executionMode": settings.execution_mode,
        "liveTradingEnabled": settings.live_trading_enabled,
    }


# --- monitoring: data-quality gate + feature drift, for the ops/dashboard view ---
@api.get("/monitoring")
def monitoring():
    """Pipeline health: latest data-quality report + feature-drift (PSI) status.

    Reads the artifacts the pipeline's validate/drift stages write. Returns nulls
    (not an error) before the pipeline has run, so the dashboard degrades cleanly.
    """
    research = settings.data_dir / "research"
    data_health = _read_json(research / "data_health.json")
    drift = _read_json(research / "drift.json")
    return {
        "dataHealth": data_health,
        "drift": drift,
        "status": {
            "data": "ok" if (data_health or {}).get("ok") else "unknown",
            "drift": (drift or {}).get("overall", "unknown"),
        },
    }


# --- validation: robustness research (rolling-window, window sweep, …) ---
@api.get("/validation")
def validation():
    """Realism/robustness studies served from data/research/*.json.

    Aggregates the validation artifacts the ml.research scripts write. Each key is
    null until its study has run, so the page degrades cleanly on a cold checkout.
    """
    research = settings.data_dir / "research"
    return {
        "rollingWindow": _read_json(research / "rolling_window.json"),
        "windowComparison": _read_json(research / "window_comparison.json"),
        "regimeModels": _read_json(research / "regime_models.json"),
        "ood": _read_json(research / "ood.json"),
        "confidence": _read_json(research / "confidence.json"),
        "onlineLearning": _read_json(research / "online_learning.json"),
    }


# --- signals: real, from model.predict_proba via the ml/inference artifacts ---
@api.get("/signals", response_model=list[Signal])
def signals(type: str | None = None):
    data, _ = store.get_signals(type)
    return data


@api.get("/signals/meta")
def signals_meta():
    return {**store.signals_meta(), "source": store.get_signals()[1]}


# --- models: real registry + feature importance from ml/training ---
@api.get("/models")
def models():
    data, _ = store.get_models()
    return data


# --- portfolio/risk: signals -> proposed orders, nothing executed ---
@api.get("/portfolio/proposed-orders")
def proposed_orders():
    sigs, source = store.get_signals()
    result = propose_orders(sigs)
    return {
        "source": source,
        "orders": [o.model_dump() for o in result["orders"]],
        "summary": result["summary"],
    }


# --- execution: status + a safe end-to-end preview (never live) ---
@api.get("/execution")
def execution_status():
    adapter = get_execution_adapter(settings)
    return {
        "mode": settings.execution_mode,
        "broker": settings.broker_provider,
        "liveTradingEnabled": settings.live_trading_enabled,
        "adapter": adapter.health(),
    }


@api.get("/execution/preview")
def execution_preview():
    """Run signals -> risk -> execution adapter once, just to show the chain."""
    sigs, source = store.get_signals()
    proposed = propose_orders(sigs)["orders"]
    adapter = get_execution_adapter(settings)
    try:
        result = adapter.submit(proposed, store.latest_prices())
        return {"source": source, "result": result.model_dump()}
    except (NotImplementedError, RuntimeError) as e:
        # paper without creds / live without sign-off: report, don't 500
        return {"source": source, "result": None, "note": str(e), "adapter": adapter.health()}


# --- backtest: real walk-forward, cost-aware, plus the series it feeds ---
@api.get("/metrics", response_model=list[Metric])
def metrics():
    """Dashboard KPIs - six off the latest backtest, two off the live book."""
    return backtest_service.dashboard_metrics()


@api.get("/equity", response_model=list[MetricPoint])
def equity(range: int = 0):
    series = backtest_service.equity_series()  # real backtest NAV vs QQQ
    return series[-range:] if range > 0 else series


@api.get("/trades", response_model=list[Trade])
def trades():
    return backtest_service.trades()  # real closed-trade ledger from the backtest


@api.post("/backtests")
def backtests(req: BacktestRequest | None = None):
    """Run a walk-forward, cost-aware backtest and return the whole result.

    The honest path: walk-forward OOS signals -> the live risk engine ->
    net-of-cost equity vs buy-and-hold QQQ. Re-runs are fast off cached predictions.
    """
    return backtest_service.run((req or BacktestRequest()).to_engine_config())


@api.get("/risk")
def risk():
    """Real portfolio risk, aggregated from the live proposed book and price data."""
    return risk_service.build_risk_summary()


@api.post("/research", response_model=RagResponse)
async def research(req: ResearchRequest):
    await asyncio.sleep(0.4)  # TODO: swap in real RAG once the LLM side exists
    return mock.rag_response(req.prompt)


# --- websocket: live-ish price/signal ticks at /api/ws/signals ---
@api.websocket("/ws/signals")
async def ws_signals(ws: WebSocket):
    await ws.accept()
    rng = random.Random()
    try:
        while True:
            base, _ = store.get_signals()
            tick = [
                {
                    "ticker": s["ticker"],
                    "price": round(s["price"] * (1 + (rng.random() - 0.5) * 0.004), 2),
                    "change": round(s["change"] + (rng.random() - 0.5) * 0.2, 2),
                    "confidence": min(99, max(1, int(s["confidence"] + (rng.random() - 0.5) * 4))),
                }
                for s in base
            ]
            await ws.send_json({"type": "tick", "data": tick})
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        return


app.include_router(api)
