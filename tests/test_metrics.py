"""Performance/risk statistics. The numbers here are hand-checkable on purpose."""
from __future__ import annotations

import math

import pytest
from backtesting import metrics as M


def test_max_drawdown_known_curve():
    # peak 110, trough 88 -> 88/110 - 1 = -0.20
    assert M._max_drawdown([100, 110, 88, 99]) == pytest.approx(-0.20)


def test_max_drawdown_monotonic_up_is_zero():
    assert M._max_drawdown([100, 101, 102, 103]) == 0.0


def test_annual_return_doubling_in_one_year():
    # equity doubles over exactly one year (periods_per_year == n_periods)
    assert M._ann_return([100, 200], periods_per_year=1) == pytest.approx(1.0)


def test_annual_return_flat_is_zero():
    assert M._ann_return([100, 100, 100], periods_per_year=4) == 0.0


def test_sharpe_matches_closed_form():
    # returns [0.10, 0.00]: mean 0.05, sample-std sqrt(0.005)=0.070710...
    # with periods_per_year=2 the annualisation factor is sqrt(2),
    # so sharpe = 0.05 / 0.070710 * sqrt(2) = 1.0 exactly.
    returns = [0.10, 0.00]
    equity = [100.0, 110.0, 110.0]
    perf = M.performance_metrics(returns, equity, bench_returns=[0.0, 0.0], periods_per_year=2)
    assert perf["sharpe"] == pytest.approx(1.0, abs=1e-9)


def test_performance_metrics_has_full_contract():
    perf = M.performance_metrics(
        [0.01, -0.02, 0.03, 0.00],
        [100, 101, 99, 102, 102],
        [0.005, -0.01, 0.02, 0.00],
        periods_per_year=52,
    )
    for key in (
        "cagr", "totalReturn", "sharpe", "sortino", "volatility",
        "maxDrawdown", "benchCorrelation", "beta", "excessReturn", "timeUnderWater",
    ):
        assert key in perf
    assert set(perf["timeUnderWater"]) == {"fraction", "longestDays"}


def test_time_under_water_fraction_in_range():
    tuw = M._time_under_water([100, 90, 95, 105, 102], periods_per_year=252)
    assert 0.0 <= tuw["fraction"] <= 1.0
    assert tuw["longestDays"] >= 0


def test_trade_stats_win_rate_and_profit_factor():
    trades = [
        {"ret": 6.0, "pnl": 500, "hold": 4},
        {"ret": 4.0, "pnl": 300, "hold": 3},
        {"ret": -3.0, "pnl": -200, "hold": 2},
        {"ret": -1.5, "pnl": -100, "hold": 5},
    ]
    s = M.trade_stats(trades)
    assert s["numTrades"] == 4
    assert s["winRate"] == pytest.approx(0.5)
    # gross win 800 / gross loss 300
    assert s["profitFactor"] == pytest.approx(800 / 300, abs=0.01)


def test_trade_stats_empty():
    s = M.trade_stats([])
    assert s["numTrades"] == 0
    assert s["profitFactor"] == 0.0


def test_annualised_turnover():
    # mean per-rebalance turnover 0.2, 52 rebalances/yr -> 10.4
    assert M.annualised_turnover([0.1, 0.3, 0.2], periods_per_year=52) == pytest.approx(0.2 * 52, abs=1e-6)
    assert M.annualised_turnover([], periods_per_year=52) == 0.0


def test_sortino_only_penalises_downside():
    # all-positive returns -> no downside deviation -> sortino guards to 0
    perf = M.performance_metrics([0.01, 0.02, 0.015], [100, 101, 103, 104.5], [0, 0, 0], 52)
    assert perf["sortino"] == 0.0
    assert math.isfinite(perf["sharpe"])
