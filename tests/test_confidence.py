"""Confidence-weighted sizing and probability calibration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.research.confidence import calibration, sizing_comparison


def _oos(n_dates: int = 40, n_names: int = 15, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")
    rows = []
    for dt in dates:
        for j in range(n_names):
            p_buy = float(rng.uniform(0.2, 0.8))
            is_buy = rng.uniform() < p_buy  # calibrated by construction
            label = 2 if is_buy else int(rng.integers(0, 2))
            rows.append({
                "date": dt, "ticker": f"T{j}", "fwd_ret_5": float(rng.normal(0, 0.02)),
                "label": label, "pred": int(rng.integers(0, 3)),
                "p_avoid": 0.0, "p_hold": 0.0, "p_buy": p_buy,
            })
    return pd.DataFrame(rows)


def test_sizing_comparison_returns_both_baskets():
    res = sizing_comparison(_oos())
    assert {"sharpe", "maxDrawdown"} <= set(res["equalWeight"])
    assert {"sharpe", "maxDrawdown"} <= set(res["confidenceWeighted"])


def test_calibration_brier_and_bins():
    calib = calibration(_oos(), n_bins=8)
    assert 0.0 <= calib["brier"] <= 1.0
    assert calib["ece"] >= 0.0
    assert calib["bins"] and {"pMean", "observed", "n"} <= set(calib["bins"][0])


def test_well_calibrated_probabilities_have_low_brier():
    # labels generated as BUY with probability p_buy => Brier should be well under 0.25
    calib = calibration(_oos(n_dates=120), n_bins=10)
    assert calib["brier"] < 0.25
