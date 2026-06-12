"""Feature-group bookkeeping and the tuning search space (no heavy runs here)."""
from __future__ import annotations

import optuna

from ml.features.build import FEATURE_COLS
from ml.research.ablation import FEATURE_GROUPS
from ml.training.tune import factory_from_params, suggest_params


def test_groups_partition_the_features_exactly():
    flat = [c for cols in FEATURE_GROUPS.values() for c in cols]
    # every feature in exactly one group - no gaps, no double-counting
    assert len(flat) == len(FEATURE_COLS)
    assert set(flat) == set(FEATURE_COLS)
    assert len(set(flat)) == len(flat)


def test_suggest_params_stays_in_bounds():
    # a FixedTrial lets us exercise the search space without running a study
    trial = optuna.trial.FixedTrial({
        "n_estimators": 300, "max_depth": 5, "learning_rate": 0.05,
        "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 6,
        "reg_lambda": 1.0,
    })
    p = suggest_params(trial)
    assert p["max_depth"] == 5
    assert 0.0 < p["learning_rate"] < 1.0
    assert 0.6 <= p["subsample"] <= 1.0


def test_factory_builds_a_fitted_capable_classifier():
    clf = factory_from_params({"n_estimators": 50, "max_depth": 3, "learning_rate": 0.1,
                               "subsample": 0.8, "colsample_bytree": 0.8,
                               "min_child_weight": 5, "reg_lambda": 1.0})
    assert hasattr(clf, "fit") and hasattr(clf, "predict_proba")
    # searched params land on the estimator; fixed base params survive
    assert clf.get_params()["max_depth"] == 3
    assert clf.get_params()["objective"] == "multi:softprob"
