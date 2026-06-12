"""
Execution layer.

The only place an order can actually be acted on. Picked by EXECUTION_MODE:

    backtest -> BacktestExecutionAdapter  (simulated fills, implemented)
    paper    -> PaperExecutionAdapter     (Alpaca paper, implemented)
    live     -> LiveExecutionAdapter      (real orders, off by design)

Neither the signal engine nor the frontend ever import or call an adapter
directly. They go through the risk layer, which proposes orders that an adapter
may or may not execute.
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
