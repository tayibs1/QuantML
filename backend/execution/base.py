"""
Execution interface plus the shared order/fill models.

ProposedOrder is what the risk layer emits. An ExecutionAdapter turns proposed
orders into Fills, or rejects them. Every adapter (backtest, paper, live)
implements the same submit() contract, so switching execution modes never has to
touch the signal engine, the risk layer, or the frontend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["backtest", "paper", "live"]


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ProposedOrder(BaseModel):
    """What the risk layer emits: an intention to trade, not a trade."""
    ticker: str
    side: OrderSide
    target_weight: float = Field(..., description="Target portfolio weight (0-1).")
    quantity: float | None = Field(None, description="Shares, if sized.")
    signal: Literal["BUY", "HOLD", "AVOID"]
    confidence: float
    reason: str = ""


class Fill(BaseModel):
    ticker: str
    side: OrderSide
    quantity: float
    price: float
    cost: float = 0.0  # commissions + slippage, in currency
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    mode: Mode = "backtest"


class ExecutionResult(BaseModel):
    mode: Mode
    accepted: list[Fill] = []
    rejected: list[dict] = []
    note: str = ""


class ExecutionAdapter(ABC):
    """Common contract for every execution mode."""

    mode: Mode

    @abstractmethod
    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        """Act on proposed orders given reference prices and account equity."""

    def health(self) -> dict:
        """Lightweight status for the API's /execution endpoint."""
        return {"mode": self.mode, "ready": True}
