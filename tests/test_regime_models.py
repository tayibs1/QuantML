"""Regime-specialised models: both tracks produced, thin specialists fall back."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.labels.outperformance import make_labels
from ml.research.regime_models import regime_walk_forward


def _tiny_model():
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=8, max_depth=2, num_class=3, objective="multi:softprob",
        tree_method="hist", verbosity=0, n_jobs=1,
    )


def _synthetic(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=90, freq="B")
    names = [f"T{i}" for i in range(6)]
    rows = []
    for i, dt in enumerate(dates):
        for nm in names:
            rows.append({
                "date": dt, "ticker": nm,
                "f1": rng.normal(), "f2": rng.normal(), "f3": rng.normal(),
                "fwd_ret_5": rng.normal(0, 0.02),
                # alternate regimes so both specialists see data every fold
                "regime": "Bull" if i % 2 == 0 else "Bear",
            })
    d = make_labels(pd.DataFrame(rows))
    return d


def test_both_tracks_cover_every_test_row():
    d = _synthetic()
    gen, ens = regime_walk_forward(
        d, model_factory=_tiny_model, feature_cols=["f1", "f2", "f3"], min_regime_rows=40,
    )
    assert not gen.empty and not ens.empty
    assert {"date", "ticker", "pred", "p_buy"} <= set(gen.columns)
    # routing partitions the test set, so the ensemble scores the same rows as general
    assert len(ens) == len(gen)


def test_thin_specialists_fall_back_to_general():
    d = _synthetic()
    # an impossibly high threshold means no specialist ever fits -> ensemble == general
    gen, ens = regime_walk_forward(
        d, model_factory=_tiny_model, feature_cols=["f1", "f2", "f3"],
        min_regime_rows=10_000,
    )
    merged = gen.merge(ens, on=["date", "ticker"], suffixes=("_g", "_e"))
    assert (merged["pred_g"] == merged["pred_e"]).all()
