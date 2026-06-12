"""
Stage 3: training + walk-forward validation.

- Labels: cross-sectional terciles of the 5-day forward return per date
  (BUY = top third, AVOID = bottom third, HOLD = middle). Balanced classes, and
  the model ends up learning to rank names rather than chase absolute returns.
- Model: XGBoost multi-class (softprob).
- Validation: expanding-window walk-forward, each fold tested strictly on the
  future and aggregated out-of-sample. No random splits, those would leak.
- Artifacts: final model (fit on everything) + meta + a model card carrying the
  real OOS metrics and gain-based feature importance.

    python -m ml.training.walk_forward

Writes:
    data/models/xgb_signal.joblib   trained classifier (for inference)
    data/models/xgb_signal.meta.json
    data/models/model_card.json     ModelRecord[] + featureImportance[]
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier

from ml import paths
from ml.features.build import FEATURE_COLS, FEATURE_LABELS

# labels are defined once, over in ml.labels - that's the Y of the problem
from ml.labels.outperformance import BUY, CLASS_TO_SIGNAL, make_labels

N_FOLDS = 6
INITIAL_TRAIN_FRAC = 0.40
SEED = 42

# anything with .fit(X, y) and .predict_proba(X) plugs into walk_forward()
ModelFactory = Callable[[], object]

# These are the tuned params from the Optuna walk-forward search (ml/training/tune.py):
# OOS Sharpe 1.19 vs 1.00 on the old hand-picked defaults, and the improvement
# clears the Deflated Sharpe haircut (DSR ~1.0), so it's a real lift, not luck from
# 30 trials. Promoted to the champion config on 2026-06-12.
XGB_PARAMS = dict(
    n_estimators=350,
    max_depth=5,
    learning_rate=0.0875512070847474,
    subsample=0.8984173590845637,
    colsample_bytree=0.8247827530574988,
    min_child_weight=5,
    reg_lambda=0.5683038138650235,
    objective="multi:softprob",
    num_class=3,
    tree_method="hist",
    importance_type="gain",
    eval_metric="mlogloss",
    random_state=SEED,
    n_jobs=0,
)


def _new_model() -> XGBClassifier:
    return XGBClassifier(**XGB_PARAMS)


def walk_forward(
    d: pd.DataFrame,
    model_factory: ModelFactory = _new_model,
    feature_cols: list[str] | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Expanding-window OOS predictions across the timeline.

    model_factory lets the same fold logic drive any classifier (the baselines
    reuse it for an apples-to-apples comparison). feature_cols defaults to the
    full set but can be narrowed for the ablation study. The point is that every
    model is judged on identical train/test splits - nothing else moves.
    """
    cols = feature_cols or FEATURE_COLS
    dates = np.array(sorted(d["date"].unique()))
    n = len(dates)
    start = int(n * INITIAL_TRAIN_FRAC)
    fold = max(1, (n - start) // N_FOLDS)
    rows = []

    for k in range(N_FOLDS):
        tr_end = start + k * fold
        te_start = tr_end
        te_end = n if k == N_FOLDS - 1 else tr_end + fold
        if te_start >= n:
            break
        tr_dates = set(dates[:tr_end])
        te_dates = set(dates[te_start:te_end])
        tr = d[d["date"].isin(tr_dates)]
        te = d[d["date"].isin(te_dates)]
        if tr.empty or te.empty:
            continue

        model = model_factory()
        model.fit(tr[cols], tr["label"])
        proba = model.predict_proba(te[cols])
        out = te[["date", "ticker", "fwd_ret_5", "label"]].copy()
        out["pred"] = proba.argmax(1)
        out["p_avoid"], out["p_hold"], out["p_buy"] = proba[:, 0], proba[:, 1], proba[:, 2]
        rows.append(out)
        if verbose:
            print(f"  fold {k + 1}/{N_FOLDS}: train {len(tr):,} → test {len(te):,} "
                  f"({min(te_dates).date()}…{max(te_dates).date()})")

    return pd.concat(rows, ignore_index=True)


def strategy_metrics(oos: pd.DataFrame) -> dict:
    """OOS strategy stats off the BUY basket, on non-overlapping 5-day returns."""
    buy = oos[oos["pred"] == BUY]
    if buy.empty:
        return dict(sharpe=0.0, cagr=0.0, maxDrawdown=0.0)
    basket = buy.groupby("date")["fwd_ret_5"].mean().sort_index()
    nonover = basket.iloc[::5]  # de-overlap the 5-day horizon
    if len(nonover) < 3 or nonover.std() == 0:
        return dict(sharpe=0.0, cagr=0.0, maxDrawdown=0.0)
    periods_per_year = 252 / 5
    sharpe = float(nonover.mean() / nonover.std() * np.sqrt(periods_per_year))
    equity = (1 + nonover).cumprod()
    years = len(nonover) / periods_per_year
    cagr = float(equity.iloc[-1] ** (1 / years) - 1) if years > 0 else 0.0
    maxdd = float((equity / equity.cummax() - 1).min())
    return dict(sharpe=round(sharpe, 2), cagr=round(cagr, 4), maxDrawdown=round(maxdd, 4))


def classification_metrics(oos: pd.DataFrame) -> dict:
    y = oos["label"].to_numpy()
    proba = oos[["p_avoid", "p_hold", "p_buy"]].to_numpy()
    acc = float(accuracy_score(y, oos["pred"]))
    try:
        auc = float(roc_auc_score(y, proba, multi_class="ovr", average="macro"))
    except ValueError:
        auc = float("nan")
    buy = oos[oos["pred"] == BUY]
    buy_hit = float((buy["fwd_ret_5"] > 0).mean()) if not buy.empty else 0.0
    return dict(accuracy=round(acc, 4), auc=round(auc, 4), buy_hit_rate=round(buy_hit, 4))


def main() -> None:
    paths.ensure_dirs()
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("Run `python -m ml.features.build` first.")

    feats = pd.read_parquet(paths.FEATURES_PATH)
    d = make_labels(feats)
    print(f"Training on {len(d):,} labelled rows · {d['ticker'].nunique()} names · "
          f"{d['date'].min().date()} … {d['date'].max().date()}")

    print("Walk-forward validation:")
    oos = walk_forward(d)
    clf_m = classification_metrics(oos)
    strat_m = strategy_metrics(oos)
    print(f"OOS  acc={clf_m['accuracy']:.3f}  auc={clf_m['auc']:.3f}  "
          f"buy_hit={clf_m['buy_hit_rate']:.3f}  "
          f"sharpe={strat_m['sharpe']}  cagr={strat_m['cagr']:.3f}  maxDD={strat_m['maxDrawdown']:.3f}")

    # now refit on every labelled row - this is the one we ship for inference
    print("Fitting final model on all data …")
    final = _new_model()
    final.fit(d[FEATURE_COLS], d["label"])
    joblib.dump(final, paths.MODELS_DIR / "xgb_signal.joblib")

    class_mean_fwd = d.groupby("label")["fwd_ret_5"].mean().to_dict()
    train_start, train_end = str(d["date"].min().date()), str(d["date"].max().date())
    today = date.today().isoformat()

    meta = {
        "feature_cols": FEATURE_COLS,
        "class_to_signal": {str(k): v for k, v in CLASS_TO_SIGNAL.items()},
        "class_mean_fwd_ret": {str(k): float(v) for k, v in class_mean_fwd.items()},
        "label_method": "cross-sectional terciles of 5d forward return",
        "horizon_days": 5,
        "train_start": train_start,
        "train_end": train_end,
        "trained_at": today,
        "metrics": {**clf_m, **strat_m},
        "model_name": "XGBoost-v3",
    }
    (paths.MODEL_META_PATH).write_text(json.dumps(meta, indent=2))

    # gain-based feature importance, normalised to percentages
    imp = pd.Series(final.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
    imp = (imp / imp.sum() * 100).round(2)
    feature_importance = [
        {"feature": FEATURE_LABELS[f], "key": f, "importance": float(v)}
        for f, v in imp.items()
    ]

    model_card = {
        "models": [
            {
                "id": "xgboost-v3",
                "name": "XGBoost-v3",
                "family": "Gradient Boosting",
                "status": "Champion",
                "trainingWindow": f"{train_start} … {train_end}",
                "validation": f"{N_FOLDS}-fold walk-forward",
                "sharpe": strat_m["sharpe"],
                "cagr": round(strat_m["cagr"] * 100, 1),
                "maxDrawdown": round(strat_m["maxDrawdown"] * 100, 1),
                "drift": "Low",
                "auc": clf_m["auc"],
                # fraction, not percent - the frontend multiplies by 100 to display
                "accuracy": round(clf_m["accuracy"], 4),
                "features": len(FEATURE_COLS),
                "lastTrained": today,
                "experimentId": f"exp-{today}-xgb",
            }
        ],
        "featureImportance": feature_importance,
    }
    (paths.MODEL_CARD_PATH).write_text(json.dumps(model_card, indent=2))

    print(f"Saved model + meta + card to {paths.MODELS_DIR.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
