"""Transaction-cost model and turnover accounting."""
from __future__ import annotations

import pytest
from backtesting.costs import CostModel, turnover


def test_round_trip_is_commission_plus_slippage():
    cm = CostModel(commission_bps=5.0, slippage_bps=8.0)
    assert cm.round_trip_bps == pytest.approx(13.0)


def test_cost_scales_linearly_with_turnover():
    # 13 bps round-trip on a full one-for-one book turnover = 0.0013 of equity
    cm = CostModel(commission_bps=5.0, slippage_bps=8.0)
    assert cm.cost_of_trading(1.0) == pytest.approx(0.0013)
    assert cm.cost_of_trading(0.5) == pytest.approx(0.00065)
    assert cm.cost_of_trading(2.0) == pytest.approx(0.0026)


def test_negative_turnover_costs_nothing():
    # guards against a sign slip feeding in a negative traded fraction
    cm = CostModel()
    assert cm.cost_of_trading(-1.0) == 0.0


def test_turnover_full_rotation():
    # exit A/B entirely, enter C/D entirely -> |Δw| sums to 2.0
    prev = {"A": 0.5, "B": 0.5}
    cur = {"C": 0.5, "D": 0.5}
    assert turnover(prev, cur) == pytest.approx(2.0)


def test_turnover_identical_books_is_zero():
    book = {"A": 0.4, "B": 0.6}
    assert turnover(book, book) == 0.0


def test_turnover_partial_and_entry_from_cash():
    # A trimmed 0.4->0.3, B unchanged, C is a fresh 0.2 entry
    prev = {"A": 0.4, "B": 0.3}
    cur = {"A": 0.3, "B": 0.3, "C": 0.2}
    assert turnover(prev, cur) == pytest.approx(0.1 + 0.0 + 0.2)
