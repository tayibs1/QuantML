"""
Execution layer.

The ONLY place an order can be acted upon. Selected by `EXECUTION_MODE`:

    backtest → BacktestExecutionAdapter  (simulated fills — implemented)
    paper    → PaperExecutionAdapter     (Alpaca paper — stub interface)
    live     → LiveExecutionAdapter      (real orders — disabled by design)

The ML signal engine and the frontend never import or call adapters directly;
they go through the Portfolio/Risk layer, which proposes orders that an adapter
may (or may not) execute.
"""
from .base import (
    ExecutionAdapter,
    ExecutionResult,
    Fill,
    OrderSide,
    ProposedOrder,
)
from .factory import get_execution_adapter

__all__ = [
    "ExecutionAdapter",
    "ExecutionResult",
    "Fill",
    "OrderSide",
    "ProposedOrder",
    "get_execution_adapter",
]
