"""
Transaction-cost model for the backtest engine.

Every rebalance moves the book; that movement is not free. We charge two things
against each rebalance, both proportional to **turnover** (the one-way fraction
of the book that changes):

    commission  — broker/exchange fees, in basis points of traded notional
    slippage    — the gap between the decision price and the achieved fill,
                  in basis points (market impact + spread)

Turnover is measured as 0.5 * Σ|w_t - w_{t-1}| (one-way), so a full liquidation
and re-entry into entirely new names is 100% turnover and is charged once on the
way out and once on the way in — i.e. on the full Σ|Δw|. We therefore charge on
Σ|Δw| directly (round-trip aware) rather than halving it.

Costs are deducted from the period return, so the equity curve, drawdown, Sharpe
and every downstream metric are reported **net of costs** — the honest number.
"""
from __future__ import annotations

from dataclasses import dataclass

_BPS = 1e-4


@dataclass(frozen=True)
class CostModel:
    """Linear cost model in basis points of traded notional."""

    commission_bps: float = 5.0
    slippage_bps: float = 8.0

    @property
    def round_trip_bps(self) -> float:
        return self.commission_bps + self.slippage_bps

    def cost_of_trading(self, traded_notional_fraction: float) -> float:
        """Cost (as a fraction of equity) of trading `Σ|Δw|` of the book.

        `traded_notional_fraction` is the sum of absolute weight changes across
        all names at a rebalance (entries + exits). Returns the fraction of
        portfolio equity consumed by commission + slippage on that trade.
        """
        return max(0.0, traded_notional_fraction) * self.round_trip_bps * _BPS


def turnover(prev: dict[str, float], cur: dict[str, float]) -> float:
    """One-rebalance traded notional: Σ over the union of names of |w_cur - w_prev|.

    A name appearing only in `prev` is a full exit; only in `cur` a full entry;
    in both, the absolute change. This is the quantity the cost model charges on
    and the raw material for the annualised-turnover metric.
    """
    names = set(prev) | set(cur)
    return float(sum(abs(cur.get(t, 0.0) - prev.get(t, 0.0)) for t in names))
