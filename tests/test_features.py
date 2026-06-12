"""Feature pipeline: the contract, the cross-sectional standardisation, and that
the forward-return target is genuinely forward-looking."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.build import FEATURE_COLS, compute_features


def test_all_features_present_and_finite(synthetic_features):
    for col in FEATURE_COLS:
        assert col in synthetic_features.columns
    assert not synthetic_features[FEATURE_COLS].isna().any().any()


def test_output_is_sorted_by_date_then_ticker(synthetic_features):
    expected = synthetic_features.sort_values(["date", "ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(synthetic_features, expected)


def test_cross_sectional_zscore_is_standardised(synthetic_features):
    # within any single date a z-scored feature has ~0 mean and ~1 sd
    a_date = synthetic_features["date"].iloc[len(synthetic_features) // 2]
    day = synthetic_features[synthetic_features["date"] == a_date]["ret_20"]
    assert day.mean() == pytest.approx(0.0, abs=0.05)
    assert day.std(ddof=1) == pytest.approx(1.0, abs=0.1)


def test_forward_target_is_actually_forward(synthetic_ohlcv):
    # fwd_ret_5 at date t must equal close[t+5]/close[t]-1 computed from raw prices
    feats = compute_features(synthetic_ohlcv)
    ticker = "TK00"
    raw = synthetic_ohlcv[synthetic_ohlcv["ticker"] == ticker].sort_values("date")
    raw = raw.assign(manual=raw["close"].shift(-5) / raw["close"] - 1.0)
    ref = raw.set_index("date")["manual"]

    got = feats[feats["ticker"] == ticker].set_index("date")["fwd_ret_5"].dropna()
    common = got.index.intersection(ref.dropna().index)
    assert len(common) > 5
    assert np.allclose(got.loc[common].to_numpy(), ref.loc[common].to_numpy(), atol=1e-9)


def test_sparse_dates_are_dropped(make_ohlcv):
    # only 4 names exist, below the default min_names=10, so nothing survives
    thin = make_ohlcv(n_tickers=4, n_days=300)
    assert compute_features(thin, min_names=10).empty
