"""
Baseline comparison: does the gradient-boosted model actually earn its keep?

Four estimators run through the identical walk-forward folds - same dates, same
features, same labels. The only thing that changes is the model. If XGBoost can't
clearly beat cross-sectional momentum and a linear model, the extra complexity
isn't justified, and saying so is the whole point of the exercise.

  - Cross-sectional momentum  the "do you even need ML?" control. No learning at
                              all: rank names by trailing return, buy the top third.
  - Logistic regression       linear baseline on the same 24 features.
  - Random forest             non-linear, bagged (not boosted) baseline.
  - XGBoost                   the champion.

    python -m ml.training.baselines

Reuses the existing model card's featureImportance and rewrites models[] with the
full comparison, so the /models page table shows real baselines instead of a
single champion. Also drops the raw table at data/models/baselines.json.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.labels.outperformance import make_labels
from ml.training.walk_forward import (
    N_FOLDS,
    SEED,
    _new_model,
    classification_metrics,
    strategy_metrics,
    walk_forward,
)


class MomentumBaseline:
    """Cross-sectional momentum with no learning.

    Features arrive already z-scored across the universe per date, so the trailing
    return feature is effectively a per-day rank. We score each class by how close
    that rank sits to the centre of its tercile (a standard normal splits into
    thirds at z ~ +/-0.43, with tercile means near +/-1.09). That makes the BUY
    probability rise monotonically with momentum - the canonical "buy past winners"
    control that any real model has to beat.
    """

    # tercile means of a standard normal: avoid, hold, buy
    _CENTERS = np.array([-1.09, 0.0, 1.09])

    def __init__(self, feature: str = "ret_20", scale: float = 1.0):
        self.feature = feature
        self.scale = scale

    def fit(self, X, y=None):  # nothing to learn - that's the point
        return self

    def predict_proba(self, X):
        z = np.asarray(X[self.feature], dtype=float)
        logits = -self.scale * (z[:, None] - self._CENTERS[None, :]) ** 2
        logits -= logits.max(axis=1, keepdims=True)
        e = np.exp(logits)
        return e / e.sum(axis=1, keepdims=True)


def _logistic() -> LogisticRegression:
    # features are already standardised, so a plain multinomial LR is well-conditioned
    return LogisticRegression(max_iter=1000, C=0.5, random_state=SEED)


def _random_forest() -> RandomForestClassifier:
    # min_samples_leaf is deliberately large - financial labels are noisy and deep
    # leaves just memorise
    return RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=50,
        n_jobs=-1, random_state=SEED,
    )


# name, family, status, factory  - ordering here is the table ordering
MODELS = [
    ("XGBoost-v3", "Gradient Boosting", "Champion", _new_model),
    ("Random Forest", "Bagged Trees", "Baseline", _random_forest),
    ("Logistic Regression", "Linear", "Baseline", _logistic),
    ("Cross-sectional Momentum", "Rule-based", "Baseline", lambda: MomentumBaseline()),
]


def _record(name, family, status, oos, window, today) -> dict:
    clf = classification_metrics(oos)
    strat = strategy_metrics(oos)
    slug = name.lower().replace(" ", "-").replace("/", "-")
    return {
        "id": slug,
        "name": name,
        "family": family,
        "status": status,
        "trainingWindow": window,
        "validation": f"{N_FOLDS}-fold walk-forward",
        "sharpe": strat["sharpe"],
        "cagr": round(strat["cagr"] * 100, 1),
        "maxDrawdown": round(strat["maxDrawdown"] * 100, 1),
        "drift": "Low",
        "auc": clf["auc"],
        "accuracy": round(clf["accuracy"], 4),  # fraction; frontend multiplies by 100
        "features": len(FEATURE_COLS),
        "lastTrained": today,
        "experimentId": f"exp-{today}-{slug}",
        # extra fields the schema ignores but the comparison artifact keeps
        "buyHitRate": round(clf["buy_hit_rate"], 4),
    }


def run_comparison(d: pd.DataFrame) -> list[dict]:
    """Evaluate every model on the shared folds and return their records."""
    window = f"{d['date'].min().date()} … {d['date'].max().date()}"
    today = date.today().isoformat()
    records = []
    for name, family, status, factory in MODELS:
        oos = walk_forward(d, model_factory=factory, verbose=False)
        rec = _record(name, family, status, oos, window, today)
        records.append(rec)
        print(f"  {name:26} sharpe={rec['sharpe']:>5}  cagr={rec['cagr']:>6}%  "
              f"auc={rec['auc']:.3f}  acc={rec['accuracy'] * 100:.1f}%  "
              f"buy_hit={rec['buyHitRate'] * 100:.1f}%")
    return records


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("Run `python -m ml.features.build` first.")

    feats = pd.read_parquet(paths.FEATURES_PATH)
    d = make_labels(feats)
    print(f"Baseline comparison on {len(d):,} rows · {d['ticker'].nunique()} names · "
          f"{N_FOLDS}-fold walk-forward\n")
    records = run_comparison(d)

    # XGBoost should beat the others - check it actually does, and say so plainly
    champ = next(r for r in records if r["status"] == "Champion")
    best_base = max((r for r in records if r["status"] == "Baseline"), key=lambda r: r["sharpe"])
    edge = round(champ["sharpe"] - best_base["sharpe"], 2)
    verdict = (
        f"XGBoost Sharpe {champ['sharpe']} vs best baseline "
        f"({best_base['name']}) {best_base['sharpe']} - edge {edge:+}"
    )
    print(f"\n{verdict}")

    # write the raw comparison table
    paths.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    (paths.MODELS_DIR / "baselines.json").write_text(json.dumps({
        "generatedAt": date.today().isoformat(),
        "validation": f"{N_FOLDS}-fold expanding walk-forward",
        "note": "Identical folds/features/labels across all models. Signal-quality "
                "(frictionless basket) metrics, not net-of-cost.",
        "verdict": verdict,
        "models": records,
    }, indent=2))

    # fold the comparison into the model card, keeping its featureImportance
    card_path = paths.MODEL_CARD_PATH
    card = json.loads(card_path.read_text()) if card_path.exists() else {"featureImportance": []}
    # schema-only fields for models[] (drop the extra buyHitRate)
    card["models"] = [{k: v for k, v in r.items() if k != "buyHitRate"} for r in records]
    card_path.write_text(json.dumps(card, indent=2))
    print(f"Updated {card_path.relative_to(paths.REPO_ROOT)} and baselines.json")


if __name__ == "__main__":
    main()
