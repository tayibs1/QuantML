"""
Paper execution. Stub for now - the interface is here, the wiring isn't.

This is where Alpaca paper trading slots in later. Same contract as the backtest
adapter, so turning it on is purely additive: implement submit() against the
Alpaca paper API, set EXECUTION_MODE=paper and BROKER_PROVIDER=alpaca. Nothing in
the signal engine, risk layer, or frontend has to change.
"""
from __future__ import annotations

from .base import ExecutionAdapter, ExecutionResult, ProposedOrder


class PaperExecutionAdapter(ExecutionAdapter):
    mode = "paper"

    def __init__(self, broker_provider: str = "none", api_key: str = "", api_secret: str = ""):
        self.broker_provider = broker_provider
        self._api_key = api_key
        self._api_secret = api_secret
        # once this is real:
        #   from alpaca.trading.client import TradingClient
        #   self.client = TradingClient(api_key, api_secret, paper=True)

    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        # TODO(paper): turn each ProposedOrder into an Alpaca MarketOrderRequest,
        # submit to the paper account, then map the broker fills back to Fill[]
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
            "note": "Interface is ready - wire up Alpaca paper to enable it.",
        }
