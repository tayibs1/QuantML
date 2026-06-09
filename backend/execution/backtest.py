"""
Backtest / simulated execution — IMPLEMENTED.

Fills every proposed order at the reference price plus slippage, and books a
commission. No external broker; this is what powers backtests and the default
EXECUTION_MODE=backtest.
"""
from __future__ import annotations

from .base import ExecutionAdapter, ExecutionResult, Fill, OrderSide, ProposedOrder


class BacktestExecutionAdapter(ExecutionAdapter):
    mode = "backtest"

    def __init__(self, commission_bps: float = 1.0, slippage_bps: float = 2.0):
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps

    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        accepted: list[Fill] = []
        rejected: list[dict] = []

        for o in orders:
            price = prices.get(o.ticker)
            if price is None or price <= 0:
                rejected.append({"ticker": o.ticker, "reason": "no reference price"})
                continue

            # Slippage worsens the fill in the direction of the trade.
            slip = price * self.slippage_bps / 10_000
            fill_price = price + slip if o.side == OrderSide.BUY else price - slip

            qty = o.quantity
            if qty is None:
                qty = (o.target_weight * equity) / fill_price  # size from target weight

            commission = abs(qty) * fill_price * self.commission_bps / 10_000
            accepted.append(
                Fill(
                    ticker=o.ticker,
                    side=o.side,
                    quantity=round(qty, 4),
                    price=round(fill_price, 4),
                    cost=round(commission + abs(qty) * slip, 2),
                    mode=self.mode,
                )
            )

        return ExecutionResult(
            mode=self.mode,
            accepted=accepted,
            rejected=rejected,
            note=f"Simulated fills (commission {self.commission_bps}bps, slippage {self.slippage_bps}bps).",
        )

    def health(self) -> dict:
        return {
            "mode": self.mode,
            "ready": True,
            "commission_bps": self.commission_bps,
            "slippage_bps": self.slippage_bps,
        }
