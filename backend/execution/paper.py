"""
Paper execution against the Alpaca paper-trading API.

Same contract as the backtest adapter, so turning it on is purely additive: set
EXECUTION_MODE=paper, BROKER_PROVIDER=alpaca, and provide ALPACA_API_KEY /
ALPACA_API_SECRET. Nothing in the signal engine, risk layer, or frontend changes.

We talk to Alpaca over plain HTTP (no broker SDK), the same way the data layer
hits Yahoo directly - one less dependency, and the wire format stays obvious.
Each ProposedOrder becomes a *notional* market order (dollar-sized from the risk
layer's target weight), which lets Alpaca handle fractional shares. The network
call is isolated in `_place_order` so it can be exercised offline in tests.
"""
from __future__ import annotations

from .base import ExecutionAdapter, ExecutionResult, Fill, OrderSide, ProposedOrder

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


class PaperExecutionAdapter(ExecutionAdapter):
    mode = "paper"

    def __init__(
        self,
        broker_provider: str = "none",
        api_key: str = "",
        api_secret: str = "",
        base_url: str = PAPER_ENDPOINT,
    ):
        self.broker_provider = broker_provider
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._client = None  # lazily created httpx.Client

    # --- public contract ----------------------------------------------------
    def submit(
        self,
        orders: list[ProposedOrder],
        prices: dict[str, float],
        equity: float = 1_000_000.0,
    ) -> ExecutionResult:
        self._require_config()

        accepted: list[Fill] = []
        rejected: list[dict] = []

        for o in orders:
            price = prices.get(o.ticker)
            if price is None or price <= 0:
                rejected.append({"ticker": o.ticker, "reason": "no reference price"})
                continue

            notional = round(o.target_weight * equity, 2)
            if notional <= 0:
                rejected.append({"ticker": o.ticker, "reason": "non-positive notional"})
                continue

            try:
                order = self._place_order(symbol=o.ticker, side=o.side.value, notional=notional)
            except Exception as exc:  # noqa: BLE001 - any broker/transport error becomes a rejection
                rejected.append({"ticker": o.ticker, "reason": f"broker error: {exc}"})
                continue

            # Market orders fill asynchronously: use the broker's fill if present,
            # otherwise fall back to the reference price as the best estimate.
            fill_price = float(order.get("filled_avg_price") or price)
            qty = float(order.get("filled_qty") or 0) or (notional / fill_price)
            accepted.append(
                Fill(
                    ticker=o.ticker,
                    side=o.side if isinstance(o.side, OrderSide) else OrderSide(o.side),
                    quantity=round(qty, 4),
                    price=round(fill_price, 4),
                    cost=0.0,  # Alpaca charges no commission; real slippage is unknown until filled
                    mode=self.mode,
                )
            )

        return ExecutionResult(
            mode=self.mode,
            accepted=accepted,
            rejected=rejected,
            note=f"Submitted {len(accepted)} paper order(s) to Alpaca, {len(rejected)} rejected.",
        )

    def health(self) -> dict:
        configured = self._is_configured()
        return {
            "mode": self.mode,
            "ready": configured,
            "implemented": True,
            "broker": self.broker_provider,
            "configured": configured,
            "endpoint": self._base_url,
            "note": (
                "Ready: submits notional market orders to the Alpaca paper account."
                if configured
                else "Set BROKER_PROVIDER=alpaca and ALPACA_API_KEY / ALPACA_API_SECRET to enable."
            ),
        }

    # --- internals (network isolated here so submit() is testable offline) ---
    def _is_configured(self) -> bool:
        return bool(self._api_key and self._api_secret and self.broker_provider == "alpaca")

    def _require_config(self) -> None:
        if self.broker_provider != "alpaca":
            raise RuntimeError("Paper trading requires BROKER_PROVIDER=alpaca.")
        if not (self._api_key and self._api_secret):
            raise RuntimeError(
                "Paper trading requires ALPACA_API_KEY and ALPACA_API_SECRET."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
        }

    def _http(self):
        if self._client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - only hit without httpx installed
                raise RuntimeError(
                    "httpx is required for paper trading (pip install httpx)."
                ) from exc
            self._client = httpx.Client(timeout=10.0)
        return self._client

    def _place_order(self, symbol: str, side: str, notional: float) -> dict:
        """POST a notional market order to Alpaca's paper API; return the order JSON."""
        resp = self._http().post(
            f"{self._base_url}/v2/orders",
            headers=self._headers(),
            json={
                "symbol": symbol,
                "notional": str(notional),
                "side": side,
                "type": "market",
                "time_in_force": "day",
            },
        )
        resp.raise_for_status()
        return resp.json()
