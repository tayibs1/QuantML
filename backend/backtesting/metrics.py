"""
Performance & risk statistics for a backtest.

Pure functions over plain Python lists/numpy — no I/O, no global state — so they
are trivial to unit-test and reason about. Everything is computed from the
**net-of-cost** period-return series and the closed-trade ledger the engine
produces.

Conventions
-----------
- `returns`        : per-period simple returns of the strategy (net of costs).
- `bench_returns`  : per-period simple returns of the benchmark, same length.
- `periods_per_year`: 252 / rebalance_days (e.g. weekly ≈ 50.4).
- Risk-free rate is taken as 0 (excess-return Sharpe over cash ≈ flat in this
  regime); documented here rather than silently assumed.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def _ann_return(equity: Sequence[float], periods_per_year: float) -> float:
    """Compound annual growth rate from an equity curve (first point = base)."""
    if len(equity) < 2 or equity[0] <= 0:
        return 0.0
    total = equity[-1] / equity[0]
    years = (len(equity) - 1) / periods_per_year
    if years <= 0 or total <= 0:
        return 0.0
    return float(total ** (1.0 / years) - 1.0)


def _max_drawdown(equity: Sequence[float]) -> float:
    """Worst peak-to-trough decline (negative number, e.g. -0.21)."""
    peak = -math.inf
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return float(mdd)


def _time_under_water(equity: Sequence[float], periods_per_year: float) -> dict:
    """Fraction of time below the prior peak + the longest underwater stretch."""
    peak = -math.inf
    under = 0
    longest = 0
    run = 0
    for v in equity:
        peak = max(peak, v)
        if v < peak:
            under += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    n = len(equity)
    frac = under / n if n else 0.0
    longest_days = longest / periods_per_year * 252.0  # express in trading days
    return {"fraction": round(frac, 4), "longestDays": int(round(longest_days))}


def performance_metrics(
    returns: Sequence[float],
    equity: Sequence[float],
    bench_returns: Sequence[float],
    periods_per_year: float,
) -> dict:
    """Headline risk/return stats, all annualised where applicable."""
    r = np.asarray(returns, dtype=float)
    br = np.asarray(bench_returns, dtype=float)
    sqrt_ppy = math.sqrt(periods_per_year)

    mean = float(r.mean()) if r.size else 0.0
    std = float(r.std(ddof=1)) if r.size > 1 else 0.0
    downside = r[r < 0]
    dstd = float(downside.std(ddof=1)) if downside.size > 1 else 0.0

    sharpe = (mean / std * sqrt_ppy) if std > 0 else 0.0
    sortino = (mean / dstd * sqrt_ppy) if dstd > 0 else 0.0
    vol_ann = std * sqrt_ppy

    cagr = _ann_return(equity, periods_per_year)
    bench_cagr = _ann_return(
        np.concatenate([[1.0], np.cumprod(1.0 + br)]).tolist() if br.size else [1.0],
        periods_per_year,
    )
    mdd = _max_drawdown(equity)

    # Benchmark relationship (only meaningful when both series move).
    corr = 0.0
    beta = 0.0
    if r.size > 1 and br.size == r.size and br.std() > 0:
        corr = float(np.corrcoef(r, br)[0, 1])
        beta = float(np.cov(r, br, ddof=1)[0, 1] / np.var(br, ddof=1))

    total = float(equity[-1] / equity[0] - 1.0) if len(equity) >= 2 and equity[0] > 0 else 0.0
    bench_total = float(np.prod(1.0 + br) - 1.0) if br.size else 0.0

    return {
        "cagr": round(cagr, 4),
        "totalReturn": round(total, 4),
        "benchTotalReturn": round(bench_total, 4),
        "benchCagr": round(bench_cagr, 4),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "volatility": round(vol_ann, 4),
        "maxDrawdown": round(mdd, 4),
        "benchCorrelation": round(corr, 2),
        "beta": round(beta, 2),
        "excessReturn": round(total - bench_total, 4),
        "timeUnderWater": _time_under_water(equity, periods_per_year),
    }


def trade_stats(trades: Sequence[dict]) -> dict:
    """Win rate, profit factor and averages from the closed-trade ledger."""
    if not trades:
        return {
            "numTrades": 0, "winRate": 0.0, "profitFactor": 0.0,
            "avgWin": 0.0, "avgLoss": 0.0, "avgHold": 0.0, "bestTrade": 0.0, "worstTrade": 0.0,
        }
    rets = [t["ret"] for t in trades]
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {
        "numTrades": len(trades),
        "winRate": round(len(wins) / len(trades), 4),
        "profitFactor": round(pf, 2) if math.isfinite(pf) else 99.99,
        "avgWin": round(float(np.mean([t["ret"] for t in trades if t["pnl"] > 0])) if wins else 0.0, 4),
        "avgLoss": round(float(np.mean([t["ret"] for t in trades if t["pnl"] < 0])) if losses else 0.0, 4),
        "avgHold": round(float(np.mean([t["hold"] for t in trades])), 1),
        "bestTrade": round(max(rets), 4),
        "worstTrade": round(min(rets), 4),
    }


def annualised_turnover(turnovers: Sequence[float], periods_per_year: float) -> float:
    """Mean per-rebalance traded notional, scaled to a yearly figure."""
    if not turnovers:
        return 0.0
    return round(float(np.mean(turnovers)) * periods_per_year, 4)
