"""Anchored weekly walk-forward: the purge must never leak a future label."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.labels.outperformance import LABEL_HORIZON, make_labels
from ml.research.rolling_window import (
    prediction_schedule,
    rolling_window_oos,
    series_metrics,
)


def test_schedule_never_trains_on_an_unrealised_label():
    # The core leakage guard: every training label's 5-day window must have closed
    # by the decision date, i.e. max_train_idx + horizon <= predict_idx.
    splits = prediction_schedule(600, step=5, embargo=LABEL_HORIZON, start_idx=120)
    assert splits
    for sp in splits:
        max_train_idx = sp.train_hi - 1
        assert max_train_idx + LABEL_HORIZON <= sp.predict_idx
        assert sp.train_lo >= 0


def test_schedule_steps_one_week_at_a_time():
    splits = prediction_schedule(400, step=5, start_idx=100)
    idxs = [sp.predict_idx for sp in splits]
    assert idxs[0] == 100
    assert all(b - a == 5 for a, b in zip(idxs, idxs[1:], strict=False))


def test_lookback_caps_training_history():
    splits = prediction_schedule(2000, lookback=252, start_idx=1000)
    assert all(sp.train_hi - sp.train_lo <= 252 for sp in splits)


def test_expanding_window_grows_over_time():
    splits = prediction_schedule(2000, start_idx=300)  # lookback=None -> anchored
    spans = [sp.train_hi - sp.train_lo for sp in splits]
    assert spans == sorted(spans)
    assert spans[-1] > spans[0]


def test_series_metrics_on_a_winning_series():
    r = pd.Series([0.01, 0.02, 0.015, 0.005, 0.012, 0.008])
    m = series_metrics(r)
    assert m["sharpe"] > 0
    assert m["hitRate"] == 1.0
    assert m["weeks"] == 6


def test_series_metrics_degenerate_is_zeroed():
    assert series_metrics(pd.Series([0.01, 0.02]))["sharpe"] == 0.0


def _tiny_model():
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=8, max_depth=2, num_class=3, objective="multi:softprob",
        tree_method="hist", verbosity=0, n_jobs=1,
    )


def _synthetic_features(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=60, freq="B")
    names = [f"T{i}" for i in range(6)]
    rows = []
    for dt in dates:
        for nm in names:
            rows.append({
                "date": dt, "ticker": nm,
                "f1": rng.normal(), "f2": rng.normal(), "f3": rng.normal(),
                "fwd_ret_5": rng.normal(0, 0.02),
            })
    return make_labels(pd.DataFrame(rows))


def test_rolling_window_runs_end_to_end():
    d = _synthetic_features()
    oos, weekly = rolling_window_oos(
        d, feature_cols=["f1", "f2", "f3"], start_idx=30, model_factory=_tiny_model,
    )
    assert not oos.empty
    assert weekly and {"date", "n", "accuracy", "basketReturn", "psi"} <= set(weekly[0])
    # predictions only ever land on dates we scheduled, never duplicated
    assert oos["date"].nunique() == len(weekly)
