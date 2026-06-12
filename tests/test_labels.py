"""Label definitions: cross-sectional terciles, uniqueness weights, triple-barrier."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.labels.outperformance import (
    AVOID,
    BUY,
    HOLD,
    average_uniqueness,
    build_label_artifacts,
    make_labels,
)
from ml.labels.triple_barrier import apply_triple_barrier, daily_volatility, triple_barrier_labels


def test_make_labels_ranks_within_a_date():
    # one date, fwd returns 1..9 -> top is BUY, bottom is AVOID, all in {0,1,2}
    d = pd.Timestamp("2024-01-02")
    df = pd.DataFrame({
        "date": [d] * 9,
        "ticker": [f"T{i}" for i in range(9)],
        "fwd_ret_5": [i / 100 for i in range(1, 10)],
    })
    out = make_labels(df).set_index("ticker")
    assert out.loc["T8", "label"] == BUY      # highest forward return
    assert out.loc["T0", "label"] == AVOID    # lowest
    assert set(out["label"]).issubset({AVOID, HOLD, BUY})


def test_make_labels_is_cross_sectional_per_date():
    # a name that's top on day 1 but bottom on day 2 should flip label
    d1, d2 = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")
    df = pd.DataFrame({
        "date": [d1, d1, d1, d2, d2, d2],
        "ticker": ["A", "B", "C", "A", "B", "C"],
        "fwd_ret_5": [0.05, 0.00, -0.05, -0.05, 0.00, 0.05],
    })
    out = make_labels(df).set_index(["date", "ticker"])["label"]
    assert out[(d1, "A")] == BUY
    assert out[(d2, "A")] == AVOID


def test_make_labels_drops_missing_target():
    df = pd.DataFrame({
        "date": [pd.Timestamp("2024-01-02")] * 3,
        "ticker": ["A", "B", "C"],
        "fwd_ret_5": [0.01, np.nan, -0.01],
    })
    out = make_labels(df)
    assert len(out) == 2
    assert "B" not in set(out["ticker"])


def test_average_uniqueness_mean_normalised(label_frame):
    _, events = build_label_artifacts(label_frame)
    w = average_uniqueness(events)
    assert w.mean() == pytest.approx(1.0, abs=1e-6)
    assert (w > 0).all()


def test_overlapping_events_have_real_dispersion():
    # fixed-horizon windows overlap by different amounts, so after mean-
    # normalisation the weights must spread out - not collapse to a flat 1.0
    df = pd.DataFrame({
        "date": np.repeat(pd.bdate_range("2024-01-01", periods=10), 4),
        "ticker": np.tile([f"T{i}" for i in range(4)], 10),
        "fwd_ret_5": np.random.default_rng(0).normal(0, 0.02, 40),
    })
    _, events = build_label_artifacts(df)
    w = average_uniqueness(events)
    assert w.std() > 0.0
    assert w.max() > 1.0
    assert w.mean() == pytest.approx(1.0, abs=1e-6)


def test_build_label_artifacts_contract(label_frame):
    labels, events = build_label_artifacts(label_frame)
    assert list(labels.columns) == ["date", "ticker", "label", "fwd_ret", "t1", "weight"]
    for col in ("date", "ticker", "t1", "horizon", "fwd_ret", "rank_pct", "weight"):
        assert col in events.columns
    assert labels["label"].isin([AVOID, HOLD, BUY]).all()


def test_triple_barrier_profit_take_on_rising_series():
    # a steadily rising series should mostly hit the upper (profit-take) barrier
    close = pd.Series(100 * (1.01 ** np.arange(60)), index=pd.RangeIndex(60))
    out = triple_barrier_labels(close, pt=2.0, sl=2.0, max_horizon=10)
    assert (out["label"] == 1).sum() > (out["label"] == -1).sum()
    assert set(out["touch"]).issubset({"pt", "sl", "time"})


def test_triple_barrier_stop_loss_on_falling_series():
    close = pd.Series(100 * (0.99 ** np.arange(60)), index=pd.RangeIndex(60))
    vol = daily_volatility(close)
    out = apply_triple_barrier(close, vol, pt=2.0, sl=2.0, max_horizon=10)
    assert (out["label"] == -1).sum() > (out["label"] == 1).sum()
    assert out["label"].isin([-1, 0, 1]).all()
