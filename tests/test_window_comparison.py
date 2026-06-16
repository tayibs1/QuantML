"""Training-window sweep: every window scored over the same aligned weeks."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.labels.outperformance import make_labels
from ml.research.window_comparison import compare_windows


def _tiny_model():
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=8, max_depth=2, num_class=3, objective="multi:softprob",
        tree_method="hist", verbosity=0, n_jobs=1,
    )


def _synthetic(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    names = [f"T{i}" for i in range(6)]
    rows = [
        {"date": dt, "ticker": nm, "f1": rng.normal(), "f2": rng.normal(),
         "f3": rng.normal(), "fwd_ret_5": rng.normal(0, 0.02)}
        for dt in dates for nm in names
    ]
    return make_labels(pd.DataFrame(rows))


def test_compare_windows_scores_each_window_and_picks_winners():
    d = _synthetic()
    res = compare_windows(
        d, windows={"short": 20, "expanding": None}, step=5, start_idx=40,
        model_factory=_tiny_model, feature_cols=["f1", "f2", "f3"],
    )
    assert set(res["windows"]) == {"short", "expanding"}
    assert res["bestBySharpe"] in res["windows"]
    assert res["steadiestByVol"] in res["windows"]
    for m in res["windows"].values():
        assert {"sharpe", "volatility", "hitRate", "weeks"} <= set(m)


def test_windows_are_evaluated_over_the_same_span():
    d = _synthetic()
    res = compare_windows(
        d, windows={"short": 20, "expanding": None}, step=5, start_idx=40,
        model_factory=_tiny_model, feature_cols=["f1", "f2", "f3"],
    )
    # aligned evaluation => identical number of scored weeks across windows
    weeks = {name: m["weeks"] for name, m in res["windows"].items()}
    assert len(set(weeks.values())) == 1
