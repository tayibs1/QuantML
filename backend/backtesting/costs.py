"""
Transaction-cost model used by the backtest.

Whenever the portfolio is rebalanced, positions are bought, sold, or resized.
These trades are not free, so the backtest deducts two costs:

- Commission: fees charged by the broker or exchange.
- Slippage: the difference between the expected trade price and the actual
  execution price, including spread and market impact.

Both costs are measured in basis points. One basis point is equal to 0.01%.

Turnover measures how much of the portfolio changes during a rebalance:

    turnover = sum(abs(new_weight - previous_weight))

We do not divide turnover by two. Selling an old position and buying a new
position are separate trades, and both sides create costs.

The calculated transaction cost is deducted directly from the portfolio's
return. This means performance measures such as total return, Sharpe ratio,
and drawdown reflect realistic returns after trading costs.
"""

from __future__ import annotations

from dataclasses import dataclass

# Convert basis points into decimal form.
# For example, 5 bps becomes 0.0005, or 0.05%.
_BPS = 1e-4


@dataclass(frozen=True)
class CostModel:
    """
    Stores the trading costs used by the backtest.

    The class is frozen because these assumptions should remain unchanged
    after the cost model has been created.
    """

    # Fee charged by the broker or exchange for each unit of traded notional.
    commission_bps: float = 5.0

    # Estimated execution cost caused by spread, market impact, and price movement.
    slippage_bps: float = 8.0

    @property
    def round_trip_bps(self) -> float:
        """
        Return the total cost applied to traded notional.

        With the default values, each unit traded costs:

            5 bps commission + 8 bps slippage = 13 bps
        """
        return self.commission_bps + self.slippage_bps

    def cost_of_trading(self, traded_notional_fraction: float) -> float:
        """
        Calculate how much of the portfolio changed during rebalancing.
        """
        valid_traded_fraction = max(0.0, traded_notional_fraction)

        return valid_traded_fraction * self.round_trip_bps * _BPS


def turnover(prev: dict[str, float], cur: dict[str, float]) -> float:
    """
    Calculate the trading cost as a percentage of the portfolio.

    The cost depends on how much of the portfolio was traded.
    Negative values are treated as zero.
    """

    # Use the union so that entries, exits, and resized positions are included.
    names = set(prev) | set(cur)

    # Missing assets are given a weight of zero.
    total_traded = sum(
        abs(cur.get(ticker, 0.0) - prev.get(ticker, 0.0))
        for ticker in names
    )

    return float(total_traded)
