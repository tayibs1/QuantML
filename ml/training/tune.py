"""
Hyperparameter search with an honest objective and an honest scorecard.

Optuna searches the XGBoost space, but two things keep it from fooling itself:

  1. The objective is the walk-forward out-of-sample Sharpe - the same expanding
     folds everything else uses. No in-sample fitting, no peeking.
  2. Every trial is logged to the trial registry, and the winner's Sharpe is then
     deflated by how many trials were run (the Deflated Sharpe Ratio). Run enough
     configs and the best one looks good by luck alone; the DSR is what tells you
     whether the search actually found something.

    python -m ml.training.tune [n_trials]   # default 30

Writes data/research/tuning.json (best params + deflated scorecard) and appends
every trial to data/research/trials.jsonl.
"""
from __future__ import annotations

import json
import sys

import optuna
import pandas as pd
from optuna.samplers import TPESampler
from xgboost import XGBClassifier

from ml import paths
from ml.labels.outperformance import make_labels
from ml.research.regime import basket_returns
from ml.research.trial_registry import deflated_sharpe_ratio, log_trial
from ml.training.walk_forward import (
    SEED,
    XGB_PARAMS,
    classification_metrics,
    strategy_metrics,
    walk_forward,
)

# keys Optuna gets to move; everything else in XGB_PARAMS stays fixed
_SEARCHED = {
    "n_estimators", "max_depth", "learning_rate", "subsample",
    "colsample_bytree", "min_child_weight", "reg_lambda",
}
_FIXED = {k: v for k, v in XGB_PARAMS.items() if k not in _SEARCHED}


def suggest_params(trial: optuna.Trial) -> dict:
    """The search space - tight enough to stay in sensible, low-overfit territory."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 150, 450, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 7),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 12),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
    }


def factory_from_params(params: dict):
    """Build an XGBoost classifier from searched params + the fixed base."""
    return XGBClassifier(**{**_FIXED, **params})


def _objective(trial: optuna.Trial, d: pd.DataFrame) -> float:
    params = suggest_params(trial)
    oos = walk_forward(d, model_factory=lambda: factory_from_params(params), verbose=False)
    strat = strategy_metrics(oos)
    clf = classification_metrics(oos)
    log_trial(
        "tuning", params,
        {"sharpe": strat["sharpe"], "auc": clf["auc"], "cagr": strat["cagr"]},
        tags=["optuna", "xgboost"],
    )
    return strat["sharpe"]


def main(n_trials: int = 30) -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("Run `python -m ml.features.build` first.")
    feats = pd.read_parquet(paths.FEATURES_PATH)
    d = make_labels(feats)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=SEED))
    print(f"Optuna · {n_trials} trials · objective = walk-forward OOS Sharpe")
    study.optimize(lambda t: _objective(t, d), n_trials=n_trials, show_progress_bar=False)

    values = [t.value for t in study.trials if t.value is not None]
    trial_std = float(pd.Series(values).std(ddof=1)) if len(values) > 1 else 0.0
    best_params = study.best_params

    # n_obs = independent OOS observations, from the same non-overlapping basket
    best_oos = walk_forward(d, model_factory=lambda: factory_from_params(best_params), verbose=False)
    n_obs = int(len(basket_returns(best_oos)))
    best_sharpe = float(study.best_value)

    dsr = deflated_sharpe_ratio(best_sharpe, n_obs, len(values), trial_std)
    baseline_sharpe = round(strategy_metrics(walk_forward(d, verbose=False))["sharpe"], 2)

    verdict = (
        f"Best OOS Sharpe {round(best_sharpe, 2)} after {len(values)} trials "
        f"(default config {baseline_sharpe}). DSR {round(dsr, 3)} - "
        + ("survives the multiple-testing haircut." if dsr > 0.9 else
           "consistent with luck once the search is accounted for.")
    )
    print(f"\n{verdict}")
    print("Best params:", json.dumps(best_params))

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "tuning.json"
    out_path.write_text(json.dumps({
        "nTrials": len(values),
        "objective": "walk-forward OOS Sharpe",
        "defaultSharpe": baseline_sharpe,
        "bestSharpe": round(best_sharpe, 3),
        "trialSharpeStd": round(trial_std, 3),
        "nObs": n_obs,
        "deflatedSharpeRatio": round(dsr, 4),
        "bestParams": best_params,
        "verdict": verdict,
    }, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    main(n)
