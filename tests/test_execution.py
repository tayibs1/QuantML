"""Execution adapters and the live-trading safety gate.

The gate is the most important thing in this file: live trading has to stay
impossible unless someone deliberately flips LIVE_TRADING_ENABLED.
"""
from __future__ import annotations

import pytest
from config import Settings
from execution import OrderSide, ProposedOrder, get_execution_adapter
from execution.backtest import BacktestExecutionAdapter
from execution.live import LiveExecutionAdapter
from execution.paper import PaperExecutionAdapter


def _order(ticker="AAA", weight=0.5):
    return ProposedOrder(
        ticker=ticker, side=OrderSide.BUY, target_weight=weight,
        signal="BUY", confidence=80.0,
    )


def test_live_mode_without_flag_is_blocked():
    s = Settings(execution_mode="live", live_trading_enabled=False)
    with pytest.raises(RuntimeError):
        s.assert_execution_allowed()


def test_backtest_mode_is_allowed():
    s = Settings(execution_mode="backtest", live_trading_enabled=False)
    s.assert_execution_allowed()  # must not raise


def test_live_adapter_refuses_to_construct_when_disabled():
    with pytest.raises(RuntimeError):
        LiveExecutionAdapter(live_trading_enabled=False)


def test_paper_adapter_is_stubbed():
    adapter = PaperExecutionAdapter()
    with pytest.raises(NotImplementedError):
        adapter.submit([_order()], {"AAA": 100.0})
    assert adapter.health()["ready"] is False


def test_factory_returns_backtest_adapter_by_default():
    s = Settings(execution_mode="backtest")
    assert get_execution_adapter(s).mode == "backtest"


def test_backtest_fill_includes_slippage_and_cost():
    adapter = BacktestExecutionAdapter(commission_bps=1.0, slippage_bps=2.0)
    res = adapter.submit([_order("AAA", 0.5)], {"AAA": 100.0}, equity=1_000_000.0)
    assert len(res.accepted) == 1
    fill = res.accepted[0]
    # a BUY fills worse than the reference price (slippage works against us)
    assert fill.price > 100.0
    assert fill.cost > 0.0


def test_backtest_rejects_orders_without_a_price():
    adapter = BacktestExecutionAdapter()
    res = adapter.submit([_order("NOPX", 0.5)], prices={}, equity=1_000_000.0)
    assert res.accepted == []
    assert res.rejected and res.rejected[0]["ticker"] == "NOPX"
