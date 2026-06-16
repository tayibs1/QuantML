"""Out-of-distribution split + era-drift measurement."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.labels.outperformance import make_labels
from ml.research.ood import era_drift, evaluate, ood_split


def _tiny_model():
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=8, max_depth=2, num_class=3, objective="multi:softprob",
        tree_method="hist", verbosity=0, n_jobs=1,
    )


def _synthetic(seed: int = 0, shift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=400, freq="B")  # 2022 -> mid-2023
    names = [f"T{i}" for i in range(6)]
    rows = []
    for dt in dates:
        mu = shift if dt >= pd.Timestamp("2023-01-01") else 0.0
        for nm in names:
            rows.append({
                "date": dt, "ticker": nm,
                "f1": rng.normal(mu, 1), "f2": rng.normal(), "f3": rng.normal(),
                "fwd_ret_5": rng.normal(0, 0.02),
            })
    return make_labels(pd.DataFrame(rows))


def test_split_is_strictly_before_and_after():
    train, test = ood_split(_synthetic(), train_end="2023-01-01")
    assert train["date"].max() < pd.Timestamp("2023-01-01")
    assert test["date"].min() >= pd.Timestamp("2023-01-01")


def test_evaluate_reports_metrics_and_era_drift():
    res = evaluate(_synthetic(), model_factory=_tiny_model, feature_cols=["f1", "f2", "f3"])
    assert {"sharpe", "auc", "accuracy"} <= set(res["metrics"])
    assert res["trainRows"] > 0 and res["testRows"] > 0
    assert {r["feature"] for r in res["eraDrift"]} == {"f1", "f2", "f3"}


def test_era_drift_flags_a_shifted_feature():
    train, test = ood_split(_synthetic(shift=4.0))
    drift = era_drift(train, test, ["f1", "f2", "f3"])
    assert drift[0]["feature"] == "f1"  # the deliberately shifted feature ranks first
    assert drift[0]["status"] == "ALERT"
