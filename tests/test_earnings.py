"""Inferred earnings-cycle features - cadence detection and, above all, causality."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.features.earnings import (
    EARNINGS_FEATURES,
    _detect_one,
    attach_earnings,
    earnings_features,
)


def _ticker_with_spikes(name="TK", n=400, period=63, spike=4.0, seed=0):
    """A volume series with a regular ~quarterly spike, plus a price column."""
    rng = np.random.default_rng(seed)
    vol = rng.uniform(1e6, 1.5e6, n)
    spikes = np.arange(period, n, period)
    vol[spikes] *= spike
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    return pd.DataFrame({
        "date": dates, "ticker": name,
        "open": close, "high": close, "low": close, "close": close, "volume": vol,
    }), spikes


def test_detector_finds_the_regular_spikes():
    df, spikes = _ticker_with_spikes()
    marks = _detect_one(df["volume"].to_numpy())
    hits = set(np.where(marks)[0])
    # most planted spikes (after the 60-day warmup) should be caught, and the
    # detector should never fire far more often than the planted cadence
    caught = [s for s in spikes if s in hits]
    assert len(caught) >= 4
    assert marks.sum() <= len(spikes) + 1


def test_days_since_is_zero_on_a_report_then_grows():
    df, spikes = _ticker_with_spikes()
    feat = earnings_features(df).reset_index(drop=True)
    first = int([s for s in spikes if s >= 60][0])
    assert feat.loc[first, "earn_days_since"] == 0.0
    assert feat.loc[first + 1, "earn_days_since"] == 1.0
    assert feat.loc[first, "earn_post5"] == 1.0


def test_features_are_strictly_causal():
    # THE important one: perturbing a future volume bar must not change any
    # earlier row's features. If it does, the feature is peeking ahead.
    df, _ = _ticker_with_spikes()
    base = earnings_features(df).reset_index(drop=True)

    cut = 250
    tampered = df.copy()
    tampered.loc[cut:, "volume"] *= 50.0   # enormous spikes, but all in the future
    after = earnings_features(tampered).reset_index(drop=True)

    cols = EARNINGS_FEATURES
    pd.testing.assert_frame_equal(base.loc[: cut - 1, cols], after.loc[: cut - 1, cols])


def test_features_vary_across_tickers_on_a_date():
    # two names reporting on different schedules must differ on a shared date,
    # otherwise the cross-sectional z-score would wipe the feature out
    a, _ = _ticker_with_spikes(name="AAA", period=63, seed=1)
    b, _ = _ticker_with_spikes(name="BBB", period=63, seed=2)
    b["volume"] = np.roll(b["volume"].to_numpy(), 25)  # shift B's cycle
    both = pd.concat([a, b], ignore_index=True)
    feat = earnings_features(both)
    pivot = feat.pivot_table(index="date", columns="ticker", values="earn_days_since")
    diff = (pivot["AAA"] - pivot["BBB"]).abs()
    assert diff.dropna().sum() > 0


def test_attach_fills_warmup_gap():
    df, _ = _ticker_with_spikes()
    feats = pd.DataFrame({"date": df["date"], "ticker": df["ticker"]})
    merged = attach_earnings(feats, df)
    assert not merged[EARNINGS_FEATURES].isna().any().any()
    # before the first detected report, days_since falls back to the ~quarter prior
    assert merged["earn_days_since"].iloc[0] == 63.0
