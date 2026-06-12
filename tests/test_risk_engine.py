"""Risk engine: signals -> proposed orders, under hard caps.

These caps are the safety story, so they get tested directly: no name over 20%,
no sector over 40%, gross never levered past 100%, and only BUYs ever sized.
"""
from __future__ import annotations

import pytest
from portfolio import RiskParams, propose_orders


def _buy(ticker, conf, sector, risk="Moderate"):
    return {"ticker": ticker, "signal": "BUY", "confidence": conf, "sector": sector, "risk": risk}


def test_no_buys_returns_empty_book():
    sigs = [
        {"ticker": "A", "signal": "HOLD", "confidence": 90, "sector": "Tech", "risk": "Low"},
        {"ticker": "B", "signal": "AVOID", "confidence": 80, "sector": "Tech", "risk": "High"},
    ]
    result = propose_orders(sigs)
    assert result["orders"] == []
    assert result["summary"]["numPositions"] == 0


def test_only_buys_are_sized():
    sigs = [
        _buy("A", 80, "Tech"),
        {"ticker": "B", "signal": "HOLD", "confidence": 95, "sector": "Tech", "risk": "Low"},
        {"ticker": "C", "signal": "AVOID", "confidence": 99, "sector": "Tech", "risk": "High"},
    ]
    tickers = {o.ticker for o in propose_orders(sigs)["orders"]}
    assert tickers == {"A"}


def test_single_name_cap_enforced():
    # 8 names all in one sector; per-name cap is 20%
    sigs = [_buy(f"T{i}", 60 + i, "Tech") for i in range(8)]
    orders = propose_orders(sigs)["orders"]
    assert orders, "expected a book"
    assert max(o.target_weight for o in orders) <= 0.20 + 1e-9


def test_sector_cap_enforced():
    # 6 Tech + 6 Health; with the 40% sector cap neither sector can dominate.
    # The cap binds pre-rounding; summing 4dp-rounded weights drifts a hair, so
    # the tolerance covers rounding (a real breach would blow well past it).
    sigs = [_buy(f"TE{i}", 70, "Tech") for i in range(6)]
    sigs += [_buy(f"HC{i}", 70, "Health") for i in range(6)]
    summary = propose_orders(sigs)["summary"]
    for _, weight in summary["exposureBySector"].items():
        assert weight <= 0.40 + 1e-3


def test_gross_never_levered():
    sigs = [_buy(f"T{i}", 90, ["Tech", "Health", "Energy"][i % 3]) for i in range(15)]
    summary = propose_orders(sigs)["summary"]
    assert summary["grossExposure"] <= 1.0 + 1e-3  # cap holds modulo 4dp rounding
    # cash is the leftover, floored at 0 (a fully-invested book holds no cash)
    assert summary["cashWeight"] == pytest.approx(max(0.0, 1.0 - summary["grossExposure"]), abs=1e-3)


def test_confidence_floor_filters():
    sigs = [_buy("A", 80, "Tech"), _buy("B", 30, "Tech")]
    orders = propose_orders(sigs, RiskParams(min_confidence=50))["orders"]
    assert {o.ticker for o in orders} == {"A"}


def test_max_positions_respected():
    sigs = [_buy(f"T{i}", 50 + i, ["Tech", "Health", "Energy", "Fin"][i % 4]) for i in range(30)]
    orders = propose_orders(sigs, RiskParams(max_positions=10))["orders"]
    assert len(orders) <= 10


def test_lower_risk_names_get_more_weight():
    # same confidence, different risk bucket -> Low keeps a larger share than
    # Elevated. Relax the caps so the risk weighting is what's actually under test
    # (otherwise both names just hit the 20% per-name cap and tie).
    sigs = [_buy("LOW", 70, "Tech", risk="Low"), _buy("HOT", 70, "Health", risk="Elevated")]
    params = RiskParams(max_name_weight=1.0, max_sector_weight=1.0)
    weights = {o.ticker: o.target_weight for o in propose_orders(sigs, params)["orders"]}
    assert weights["LOW"] > weights["HOT"]


def test_summary_contract():
    sigs = [_buy(f"T{i}", 70, "Tech") for i in range(5)]
    summary = propose_orders(sigs)["summary"]
    for key in ("grossExposure", "netExposure", "numPositions", "largestPosition",
                "exposureBySector", "cashWeight"):
        assert key in summary
