"""
Transaction-cost model for the backtest.

Every rebalance moves the book, and moving the book isn't free. Two charges,
both proportional to turnover (the fraction of the book that changes each
rebalance):

    commission   broker/exchange fees, in bps of traded notional
    slippage     gap between the decision price and the actual fill, in bps
                 (market impact + spread)

Turnover here is Sum|w_t - w_{t-1}|. Dumping the whole book and buying entirely
new names gets charged on the way out and again on the way in, i.e. on the full
Sum|dw| - so we charge on Sum|dw| directly instead of halving it.

Costs come straight out of the period return, so the equity curve, drawdown,
Sharpe, all of it land net of costs. That's the number that actually means
something.
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
        """Cost, as a fraction of equity, of trading Sum|dw| of the book.

        traded_notional_fraction is the sum of absolute weight changes over all
        names at one rebalance (entries plus exits). Returns the slice of equity
        eaten by commission + slippage on that trade.
        """
        return max(0.0, traded_notional_fraction) * self.round_trip_bps * _BPS


def turnover(prev: dict[str, float], cur: dict[str, float]) -> float:
    """Traded notional for one rebalance: sum of |w_cur - w_prev| over all names.

    A name only in prev is a full exit, only in cur a full entry, in both the
    absolute change. This is what the cost model charges on, and what the
    annualised-turnover metric is built from.
    """
    names = set(prev) | set(cur)
    return float(sum(abs(cur.get(t, 0.0) - prev.get(t, 0.0)) for t in names))
