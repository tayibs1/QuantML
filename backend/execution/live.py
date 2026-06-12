"""
Live execution. Off by design.

Real-money orders. This adapter refuses to construct at all unless
LIVE_TRADING_ENABLED=true, and even then submit() is deliberately left
unimplemented until there's a proper risk and compliance review. Not something to
flip on casually.
"""
from __future__ import annotations

from .base import ExecutionAdapter, ExecutionResult, ProposedOrder


class LiveExecutionAdapter(ExecutionAdapter):
    mode = "live"

    def __init__(self, live_trading_enabled: bool = False, broker_provider: str = "none"):
        if not live_trading_enabled:
            raise RuntimeError(
                "Live trading is disabled (LIVE_TRADING_ENABLED=false). "
                "This is a hard safety gate."
            )
        self.broker_provider = broker_provider

    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        raise NotImplementedError(
            "Live execution is not implemented. Requires risk controls, compliance "
            "review, and explicit sign-off before any real order is sent."
        )

    def health(self) -> dict:
        return {"mode": self.mode, "ready": False, "implemented": False,
                "note": "Disabled by design."}
