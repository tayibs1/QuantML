"""
QuantML backtesting package.

A walk-forward, cost-aware portfolio backtest that consumes out-of-sample model
predictions and the live risk engine to produce an honest, benchmarked equity
curve plus the full set of performance/risk statistics.

    from backtesting.engine import BacktestConfig, run_backtest
"""
from __future__ import annotations

from .costs import CostModel, turnover
from .engine import BacktestConfig, run_backtest, simulate

__all__ = ["BacktestConfig", "run_backtest", "simulate", "CostModel", "turnover"]
