"""
Backtest read/run service.

Sits between the backtest engine and the API. Two jobs:

  - serve the cached artifact (data/backtests/latest.json) to the GET endpoints
    (/api/metrics, /api/equity, /api/trades), so the whole dashboard reflects one
    consistent, real, net-of-cost backtest.
  - run a fresh backtest on demand (POST /api/backtests) with caller-chosen cost
    / rebalance settings, and persist it so the rest of the app stays in sync.

Everything falls back softly. If there's no artifact yet (pipeline hasn't run) or
the ML deps for a cold first run aren't installed, the getters drop to the seeded
mock instead of throwing. The API never goes down over this.
"""
from __future__ import annotations

import json
from typing import Optional

import mock_data as mock
from portfolio import propose_orders
from services import store

from backtesting.engine import BacktestConfig, RESULT_CACHE, run_backtest


def _load() -> Optional[dict]:
    try:
        if RESULT_CACHE.exists():
            return json.loads(RESULT_CACHE.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return None


def get_result() -> tuple[Optional[dict], str]:
    """Latest backtest artifact, or (None, 'mock') if nothing's been produced."""
    data = _load()
    return (data, "live") if data else (None, "mock")


def run(config: Optional[dict] = None) -> dict:
    """Run a backtest with the given config, persist it, fall back on failure.

    Fast in the usual case: the slow walk-forward OOS predictions are cached, so
    a re-run only re-simulates the portfolio under the new cost/rebalance settings.
    """
    cfg_kwargs = {}
    if config:
        allowed = {"rebalance", "top_n", "commission_bps", "slippage_bps", "model"}
        cfg_kwargs = {k: v for k, v in config.items() if k in allowed and v is not None}
    try:
        result = run_backtest(BacktestConfig(**cfg_kwargs))
        try:
            RESULT_CACHE.parent.mkdir(parents=True, exist_ok=True)
            RESULT_CACHE.write_text(json.dumps(result, indent=2))
        except OSError:
            pass
        return result
    except Exception as e:  # noqa: BLE001 - a failed backtest must not 500 the API
        cached, _ = get_result()
        if cached:
            return {**cached, "note": f"Returned cached result ({type(e).__name__})."}
        return _mock_result(str(e))


# --- dashboard projections: real backtest stats + live signal/risk aggregates ---
def equity_series() -> list[dict]:
    data, _ = get_result()
    if data and data.get("equity"):
        return data["equity"]
    return mock.equity_series()


def trades() -> list[dict]:
    data, _ = get_result()
    if data and data.get("trades"):
        return data["trades"]
    return mock.trades()


def dashboard_metrics() -> list[dict]:
    """The eight KPI cards - six off the backtest, two off the live book."""
    data, source = get_result()
    if not data:
        return mock.METRICS

    m = data["metrics"]
    terminal = round(1_000_000 * (1 + m["totalReturn"]))

    # the two non-performance cards come off the live book
    signals, _ = store.get_signals()
    buys = [s["confidence"] for s in signals if s.get("signal") == "BUY"]
    mean_buy_conf = round(sum(buys) / len(buys), 0) if buys else 0
    gross = round(propose_orders(signals)["summary"]["grossExposure"] * 100, 0)

    def card(key, label, value, **kw):
        return {"key": key, "label": label, "value": value, **kw}

    return [
        card("portfolio", "Backtest Value", terminal, prefix="$", decimals=0,
             delta=round(m["totalReturn"] * 100, 1), spark=1, up=m["totalReturn"] >= 0),
        card("strategy", "Strategy Return", round(m["totalReturn"] * 100, 1), suffix="%", decimals=1,
             delta=round(m["cagr"] * 100, 1), spark=2, up=m["totalReturn"] >= 0),
        card("benchmark", "Benchmark (QQQ)", round(m["benchTotalReturn"] * 100, 1), suffix="%", decimals=1,
             delta=round(m["benchCagr"] * 100, 1), spark=3, up=m["benchTotalReturn"] >= 0),
        card("sharpe", "Sharpe Ratio", m["sharpe"], decimals=2,
             delta=m["sortino"], spark=4, up=m["sharpe"] >= 0),
        card("drawdown", "Max Drawdown", round(m["maxDrawdown"] * 100, 1), suffix="%", decimals=1,
             delta=round(m["maxDrawdown"] * 100, 1), spark=5, up=False),
        card("winrate", "Win Rate", round(m["winRate"] * 100, 1), suffix="%", decimals=1,
             delta=round((m["winRate"] - 0.5) * 100, 1), spark=6, up=m["winRate"] >= 0.5),
        card("confidence", "Model Confidence", mean_buy_conf, suffix="%", decimals=0,
             delta=round(mean_buy_conf - 50, 0), spark=7, up=mean_buy_conf >= 50),
        card("exposure", "Gross Exposure", gross, suffix="%", decimals=0,
             delta=round(gross - 100, 0), spark=8, up=False),
    ]


def _mock_result(note: str) -> dict:
    """A backtest-shaped object built from seeded mock data - last resort."""
    eq = mock.equity_series()
    return {
        "source": "mock",
        "note": note,
        "config": {"rebalance": "Weekly", "top_n": 20, "commission_bps": 5.0, "slippage_bps": 8.0},
        "window": {"start": eq[0]["date"], "end": eq[-1]["date"], "rebalances": len(eq)},
        "metrics": {},
        "summaryCards": [
            {"label": "CAGR", "value": "19.4%", "tone": "bull"},
            {"label": "Sharpe Ratio", "value": "1.02", "tone": "neutral"},
            {"label": "Sortino Ratio", "value": "1.41", "tone": "neutral"},
            {"label": "Max Drawdown", "value": "-15.4%", "tone": "bear"},
            {"label": "Volatility (ann.)", "value": "18.1%", "tone": "neutral"},
            {"label": "Turnover", "value": "142%", "tone": "neutral"},
            {"label": "Win Rate", "value": "57.3%", "tone": "bull"},
            {"label": "Profit Factor", "value": "1.48", "tone": "bull"},
        ],
        "equity": eq,
        "trades": mock.trades(),
        "tradeCount": len(mock.trades()),
        "monthlyReturns": [],
    }
