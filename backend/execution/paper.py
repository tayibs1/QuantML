"""
Paper execution — STUB (interface ready, not yet wired).

This is where Alpaca paper trading plugs in later. The contract is identical to
the backtest adapter, so enabling paper trading is purely additive: implement
`submit()` against the Alpaca paper API and set EXECUTION_MODE=paper,
BROKER_PROVIDER=alpaca. No changes to the signal engine, risk layer, or frontend.
"""
from __future__ import annotations

from .base import ExecutionAdapter, ExecutionResult, ProposedOrder


class PaperExecutionAdapter(ExecutionAdapter):
    mode = "paper"

    def __init__(self, broker_provider: str = "none", api_key: str = "", api_secret: str = ""):
        self.broker_provider = broker_provider
        self._api_key = api_key
        self._api_secret = api_secret
        # When implemented:
        #   from alpaca.trading.client import TradingClient
        #   self.client = TradingClient(api_key, api_secret, paper=True)

    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        # TODO(paper): translate ProposedOrder → Alpaca MarketOrderRequest and
        # submit to the paper account; map broker fills back to Fill[].
        raise NotImplementedError(
            "Paper trading is stubbed. Set BROKER_PROVIDER=alpaca, add ALPACA_API_KEY/"
            "ALPACA_API_SECRET, and implement submit() against the Alpaca paper API."
        )

    def health(self) -> dict:
        configured = bool(self._api_key and self._api_secret and self.broker_provider == "alpaca")
        return {
            "mode": self.mode,
            "ready": False,
            "implemented": False,
            "broker": self.broker_provider,
            "configured": configured,
            "note": "Interface ready; wire Alpaca paper to enable.",
        }
