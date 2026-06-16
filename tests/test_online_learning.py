"""Retrain-cadence study: fewer refits, same weekly prediction schedule."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.labels.outperformance import make_labels
from ml.research.online_learning import cadence_oos


def _tiny_model():
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=8, max_depth=2, num_class=3, objective="multi:softprob",
        tree_method="hist", verbosity=0, n_jobs=1,
    )


def _synthetic(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=120, freq="B")
    names = [f"T{i}" for i in range(6)]
    rows = [
        {"date": dt, "ticker": nm, "f1": rng.normal(), "f2": rng.normal(),
         "f3": rng.normal(), "fwd_ret_5": rng.normal(0, 0.02)}
        for dt in dates for nm in names
    ]
    return make_labels(pd.DataFrame(rows))


def test_less_frequent_refit_does_fewer_fits_same_predictions():
    d = _synthetic()
    cols = ["f1", "f2", "f3"]
    oos_w, refits_w = cadence_oos(d, refit_every=1, start_idx=60, feature_cols=cols, model_factory=_tiny_model)
    oos_m, refits_m = cadence_oos(d, refit_every=4, start_idx=60, feature_cols=cols, model_factory=_tiny_model)

    assert refits_w > refits_m            # weekly refits more often
    assert not oos_w.empty and not oos_m.empty
    # both predict the same weeks regardless of refit cadence
    assert oos_w["date"].nunique() == oos_m["date"].nunique()
