"""
Research bookkeeping.

Tools that keep the research process honest. The headline component is the
**trial registry**: an append-only log of every backtest/experiment evaluated,
which is the raw material for correcting performance statistics for the number of
trials run (López de Prado's defence against backtest overfitting).
"""
from __future__ import annotations

from .trial_registry import (
    deflated_sharpe_ratio,
    load_trials,
    log_trial,
    probabilistic_sharpe_ratio,
    summary,
)

__all__ = [
    "log_trial",
    "load_trials",
    "summary",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
]
