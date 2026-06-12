"""Regime decomposition of the OOS BUY basket."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.labels.outperformance import AVOID, BUY
from ml.research.regime import (
    PERIODS_PER_YEAR,
    _sharpe,
    basket_returns,
    benchmark_regime,
    by_regime,
    by_year,
)


def _oos(dates, preds, rets):
    return pd.DataFrame({"date": pd.to_datetime(dates), "pred": preds, "fwd_ret_5": rets})


def test_basket_uses_only_buys_and_de_overlaps():
    dates = pd.bdate_range("2022-01-03", periods=10)
    # alternate BUY/AVOID; only BUY rows count, then every 5th date is kept
    oos = _oos(
        list(dates) + list(dates),
        [BUY] * 10 + [AVOID] * 10,
        [0.01] * 10 + [-0.5] * 10,
    )
    r = basket_returns(oos)
    assert (r > 0).all()                 # the AVOID rows (-0.5) never leak in
    assert len(r) == len(range(0, 10, 5))  # de-overlapped to every 5th date


def test_sharpe_closed_form():
    # returns [0.10, 0.00] -> mean 0.05, sd 0.0707; annualised by sqrt(PPY)
    r = pd.Series([0.10, 0.00, 0.10, 0.00])
    expected = r.mean() / r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)
    assert _sharpe(r) == pytest.approx(expected)


def test_by_year_splits_and_reports():
    d1 = pd.bdate_range("2022-01-03", periods=30)
    d2 = pd.bdate_range("2023-01-02", periods=30)
    rng = np.random.default_rng(0)
    rets = rng.normal(0.004, 0.02, 60)
    oos = _oos(list(d1) + list(d2), [BUY] * 60, rets)
    rows = by_year(oos)
    years = {r["year"] for r in rows}
    assert years == {2022, 2023}
    for r in rows:
        assert {"year", "sharpe", "meanReturn5d", "hitRate", "n"} <= set(r)
        assert 0.0 <= r["hitRate"] <= 1.0


def test_benchmark_regime_bull_and_bear():
    up = pd.DataFrame({"date": pd.bdate_range("2021-01-04", periods=260),
                       "close": np.linspace(100, 200, 260)})
    down = pd.DataFrame({"date": pd.bdate_range("2021-01-04", periods=260),
                         "close": np.linspace(200, 100, 260)})
    assert benchmark_regime(up).iloc[-1] == "Bull"
    assert benchmark_regime(down).iloc[-1] == "Bear"


def test_by_regime_partitions_returns():
    dates = pd.bdate_range("2021-06-01", periods=40)
    oos = _oos(list(dates), [BUY] * 40, np.full(40, 0.01))
    bench = pd.DataFrame({"date": pd.bdate_range("2020-06-01", periods=400),
                          "close": np.linspace(100, 300, 400)})  # steady bull
    rows = by_regime(oos, bench)
    assert all(r["regime"] in {"Bull", "Bear"} for r in rows)
    assert sum(r["n"] for r in rows) >= 1
