"""
Retrain cadence: how often does the model actually need refitting?

"Online learning" is a slightly awkward fit for gradient-boosted trees — boosting
isn't naturally incremental the way SGD is, and warm-starting just bolts more trees
on. The honest, live-relevant question underneath it is cadence: you predict every
week regardless, but refitting 350 trees on all history every single week is
expensive. How much edge do you give up if you refit every 2 / 4 / 12 weeks and reuse
the model in between?

So we hold the prediction schedule fixed (weekly, leakage-purged) and only vary how
often the model is refit, measuring OOS Sharpe against the number of refits — a direct
read on the compute/performance trade-off for a live deployment.

    python -m ml.research.online_learning

Reads features, writes data/research/online_learning.json.
"""
from __future__ import annotations

import json
import time
from datetime import date

import numpy as np
import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.labels.outperformance import make_labels
from ml.research.rolling_window import (
    _basket_series,
    _new_model,
    prediction_schedule,
    series_metrics,
)

# refit-every-N-weeks cadences to compare
CADENCES = {"weekly": 1, "biweekly": 2, "monthly": 4, "quarterly": 12}
EVAL_WEEKS = 76  # ~1.5y of weekly predictions, to keep the sweep tractable


def _predict_block(model, block: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    proba = model.predict_proba(block[cols])
    out = block[["date", "ticker", "fwd_ret_5", "label"]].copy()
    out["pred"] = proba.argmax(1)
    out["p_avoid"], out["p_hold"], out["p_buy"] = proba[:, 0], proba[:, 1], proba[:, 2]
    return out


def cadence_oos(
    d: pd.DataFrame,
    refit_every: int,
    step: int = 5,
    start_idx: int | None = None,
    model_factory=_new_model,
    feature_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Predict every week; refit the model only every `refit_every` weeks."""
    cols = feature_cols or FEATURE_COLS
    dates = np.array(sorted(d["date"].unique()))
    by_date = {dt: g for dt, g in d.groupby("date")}
    splits = prediction_schedule(len(dates), step=step, start_idx=start_idx)

    model = None
    n_refits = 0
    rows = []
    for i, sp in enumerate(splits):
        if model is None or i % refit_every == 0:
            tr = d[d["date"].isin(set(dates[sp.train_lo:sp.train_hi]))]
            if not tr.empty and tr["label"].nunique() == 3:
                model = model_factory().fit(tr[cols], tr["label"])
                n_refits += 1
        te = by_date.get(dates[sp.predict_idx])
        if model is None or te is None or te.empty:
            continue
        rows.append(_predict_block(model, te, cols))

    oos = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return oos, n_refits


def run(eval_weeks: int = EVAL_WEEKS) -> dict:
    d = make_labels(pd.read_parquet(paths.FEATURES_PATH))
    n_dates = d["date"].nunique()
    start_idx = max(252, n_dates - eval_weeks * 5)  # align all cadences to the same weeks

    results = {}
    for name, every in CADENCES.items():
        t = time.time()
        oos, n_refits = cadence_oos(d, refit_every=every, start_idx=start_idx)
        elapsed = time.time() - t
        m = series_metrics(_basket_series(oos))
        results[name] = {
            "refitEvery": every,
            "refits": n_refits,
            "seconds": round(elapsed, 1),
            "sharpe": m["sharpe"],
            "hitRate": m["hitRate"],
            "weeks": m["weeks"],
        }

    weekly = results.get("weekly", {})
    return {
        "note": "Weekly leakage-purged predictions; only the refit frequency varies. "
                "Shows the compute (refits) vs OOS Sharpe trade-off for a live cadence.",
        "generatedAt": date.today().isoformat(),
        "cadences": results,
        "fullRetrainSharpe": weekly.get("sharpe"),
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    result = run()
    print(f"{'cadence':<10} {'refits':>6} {'sharpe':>7} {'secs':>6}")
    for name, m in result["cadences"].items():
        print(f"{name:<10} {m['refits']:>6} {m['sharpe']:>7} {m['seconds']:>6}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "online_learning.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
