"""Feature drift (PSI): catch the model drifting out of its training domain."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.research.drift import feature_drift, psi


def test_psi_is_near_zero_for_same_distribution():
    rng = np.random.default_rng(0)
    a = rng.normal(size=5000)
    b = rng.normal(size=5000)
    assert psi(a, b) < 0.1


def test_psi_is_large_for_shifted_distribution():
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, size=5000)
    cur = rng.normal(3, 1, size=5000)  # big mean shift
    assert psi(ref, cur) > 0.25


def test_psi_handles_degenerate_inputs():
    assert psi([], [1, 2, 3]) == 0.0
    assert psi(np.ones(100), np.ones(50)) == 0.0  # constant feature -> no bins


def _features(n_dates=60, shift_recent=0.0, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="D")
    rows = []
    for i, d in enumerate(dates):
        mu = shift_recent if i >= n_dates - 5 else 0.0  # shift only the last 5 dates
        for _ in range(40):
            rows.append({"date": d, "ticker": "X", "f1": rng.normal(mu, 1), "f2": rng.normal()})
    return pd.DataFrame(rows)


def test_feature_drift_reports_ok_when_stable():
    result = feature_drift(_features(), feature_cols=["f1", "f2"])
    assert result["overall"] == "OK"
    assert {r["feature"] for r in result["features"]} == {"f1", "f2"}


def test_feature_drift_flags_a_shifted_feature():
    result = feature_drift(_features(shift_recent=4.0), feature_cols=["f1", "f2"])
    assert result["overall"] == "ALERT"
    top = result["features"][0]  # sorted by psi desc
    assert top["feature"] == "f1"
    assert top["status"] == "ALERT"
