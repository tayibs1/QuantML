"""
Backtesting package.

A walk-forward, cost-aware portfolio backtest. Takes out-of-sample model
predictions, runs them through the same risk engine the live system uses, and
spits out a benchmarked equity curve plus the full set of performance/risk stats.

    from backtesting.engine import BacktestConfig, run_backtest
"""
from __future__ import annotations

from .costs import CostModel, turnover
from .engine import BacktestConfig, run_backtest, simulate

__all__ = ["BacktestConfig", "run_backtest", "simulate", "CostModel", "turnover"]
