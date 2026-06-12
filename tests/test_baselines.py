"""Baseline models and the momentum control."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.training.baselines import MODELS, MomentumBaseline, _logistic, _random_forest


def test_momentum_proba_is_monotonic_in_return():
    # higher trailing-return z-score -> higher BUY probability, lower AVOID
    X = pd.DataFrame({"ret_20": [-2.0, -1.0, 0.0, 1.0, 2.0]})
    proba = MomentumBaseline().predict_proba(X)
    assert proba.shape == (5, 3)
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert np.all(np.diff(proba[:, 2]) > 0)   # p_buy strictly increasing
    assert np.all(np.diff(proba[:, 0]) < 0)   # p_avoid strictly decreasing


def test_momentum_picks_hold_at_the_median():
    # a name sitting at the cross-sectional average is a HOLD, not a coin flip
    X = pd.DataFrame({"ret_20": [0.0]})
    assert MomentumBaseline().predict_proba(X).argmax(1)[0] == 1  # HOLD


def test_momentum_fit_is_a_noop():
    m = MomentumBaseline()
    assert m.fit(pd.DataFrame({"ret_20": [1.0]}), [2]) is m


def test_baseline_factories_quack_like_classifiers():
    for factory in (_logistic, _random_forest):
        clf = factory()
        assert hasattr(clf, "fit") and hasattr(clf, "predict_proba")


def test_model_lineup_has_champion_and_baselines():
    names = [m[0] for m in MODELS]
    statuses = {m[0]: m[2] for m in MODELS}
    assert "XGBoost-v3" in names
    assert statuses["XGBoost-v3"] == "Champion"
    assert sum(1 for s in statuses.values() if s == "Baseline") >= 3
    # momentum and a linear model must be in the comparison - the honest controls
    assert any("Momentum" in n for n in names)
    assert any("Logistic" in n for n in names)
