"""
Anchored weekly walk-forward — validation the way live trading actually runs.

The 6-fold walk-forward in ml.training tells you the model generalises, but each
fold spans months: you don't see how the model behaves week to week, which is the
cadence a live book retrains on. This refits every week on all history available
*at that moment*, predicts the next cross-section, and scores it once the week's
forward return is realised. Repeat across the whole timeline.

The one thing you must not get wrong is leakage. A training label at date t is only
known at t + horizon (the 5-day forward return). So when deciding on date d, we can
only train on rows whose label window already closed by d — i.e. t <= d - horizon.
prediction_schedule() enforces that purge, and there's a test that fails if a future
row ever slips into a training split.

    python -m ml.research.rolling_window

Reads data/processed/features.parquet, writes data/research/rolling_window.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.labels.outperformance import BUY, LABEL_HORIZON, make_labels
from ml.research.drift import psi
from ml.training.walk_forward import (
    _new_model,
    classification_metrics,
    strategy_metrics,
    walk_forward,
)

STEP = 5                       # trading days between refits (one week)
PERIODS_PER_YEAR = 252 / STEP  # de-overlapped weekly observations


@dataclass(frozen=True)
class Split:
    """One refit: train on dates[train_lo:train_hi], predict on dates[predict_idx]."""
    predict_idx: int
    train_lo: int
    train_hi: int  # exclusive


def prediction_schedule(
    n_dates: int,
    *,
    step: int = STEP,
    embargo: int = LABEL_HORIZON,
    start_idx: int | None = None,
    lookback: int | None = None,
) -> list[Split]:
    """Build the (train, predict) splits, purging labels that haven't realised yet.

    train_hi = predict_idx - embargo + 1 guarantees every training label's forward
    window has closed by the decision date. lookback=None means an anchored
    (expanding) window; a value caps the training history to that many trading days.
    """
    first = start_idx if start_idx is not None else max(252, embargo + 1)
    splits: list[Split] = []
    for i in range(first, n_dates, step):
        train_hi = i - embargo + 1
        if train_hi <= 1:
            continue
        train_lo = 0 if lookback is None else max(0, train_hi - lookback)
        splits.append(Split(predict_idx=i, train_lo=train_lo, train_hi=train_hi))
    return splits


def rolling_window_oos(
    d: pd.DataFrame,
    *,
    lookback: int | None = None,
    step: int = STEP,
    start_idx: int | None = None,
    model_factory=_new_model,
    feature_cols: list[str] | None = None,
    track_drift: bool = True,
) -> tuple[pd.DataFrame, list[dict]]:
    """Run the anchored weekly scheme. Returns (oos predictions, per-week log)."""
    cols = feature_cols or FEATURE_COLS
    dates = np.array(sorted(d["date"].unique()))
    by_date = {dt: g for dt, g in d.groupby("date")}

    splits = prediction_schedule(
        len(dates), step=step, start_idx=start_idx, lookback=lookback
    )

    oos_rows: list[pd.DataFrame] = []
    weekly: list[dict] = []
    for sp in splits:
        train_dates = dates[sp.train_lo:sp.train_hi]
        tr = d[d["date"].isin(set(train_dates))]
        te = by_date.get(dates[sp.predict_idx])
        if tr.empty or te is None or te.empty:
            continue

        model = model_factory()
        model.fit(tr[cols], tr["label"])
        proba = model.predict_proba(te[cols])

        out = te[["date", "ticker", "fwd_ret_5", "label"]].copy()
        out["pred"] = proba.argmax(1)
        out["p_avoid"], out["p_hold"], out["p_buy"] = proba[:, 0], proba[:, 1], proba[:, 2]
        oos_rows.append(out)

        buy = out[out["pred"] == BUY]
        week = {
            "date": str(pd.Timestamp(dates[sp.predict_idx]).date()),
            "n": int(len(out)),
            "nBuy": int(len(buy)),
            "accuracy": round(float((out["pred"] == out["label"]).mean()), 4),
            "basketReturn": round(float(buy["fwd_ret_5"].mean()), 5) if not buy.empty else 0.0,
            "trainRows": int(len(tr)),
        }
        if track_drift:
            week["psi"] = round(
                float(np.mean([psi(tr[c], te[c]) for c in cols])), 4
            )
        weekly.append(week)

    oos = pd.concat(oos_rows, ignore_index=True) if oos_rows else pd.DataFrame()
    return oos, weekly


def series_metrics(weekly_basket: pd.Series) -> dict:
    """Risk stats off the de-overlapped weekly BUY-basket return series.

    The schedule already spaces predictions one week apart, so the basket series is
    non-overlapping by construction — no need to thin it again.
    """
    r = weekly_basket.dropna()
    if len(r) < 3 or r.std(ddof=1) == 0:
        return {"sharpe": 0.0, "cagr": 0.0, "maxDrawdown": 0.0, "hitRate": 0.0,
                "volatility": 0.0, "weeks": int(len(r))}
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))
    equity = (1 + r).cumprod()
    years = len(r) / PERIODS_PER_YEAR
    cagr = float(equity.iloc[-1] ** (1 / years) - 1) if years > 0 else 0.0
    maxdd = float((equity / equity.cummax() - 1).min())
    return {
        "sharpe": round(sharpe, 2),
        "cagr": round(cagr, 4),
        "maxDrawdown": round(maxdd, 4),
        "hitRate": round(float((r > 0).mean()), 4),
        "volatility": round(float(r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)), 4),
        "weeks": int(len(r)),
    }


def _basket_series(oos: pd.DataFrame) -> pd.Series:
    buy = oos[oos["pred"] == BUY]
    if buy.empty:
        return pd.Series(dtype=float)
    return buy.groupby("date")["fwd_ret_5"].mean().sort_index()


def run() -> dict:
    feats = pd.read_parquet(paths.FEATURES_PATH)
    d = make_labels(feats)

    # baseline: the existing 6-fold expanding walk-forward
    base_oos = walk_forward(d, verbose=False)
    baseline = {**classification_metrics(base_oos), **strategy_metrics(base_oos)}

    # the realistic version: refit every week on all data available at the time
    oos, weekly = rolling_window_oos(d)
    rolling = {**classification_metrics(oos), **series_metrics(_basket_series(oos))}

    return {
        "note": "Anchored weekly walk-forward (refit each week on prior data only, "
                "5-day label purge). Compared against the 6-fold baseline.",
        "generatedAt": date.today().isoformat(),
        "baseline": baseline,
        "rolling": rolling,
        "weekly": weekly,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    result = run()

    b, r = result["baseline"], result["rolling"]
    print(f"6-fold baseline : sharpe={b['sharpe']:>5}  auc={b['auc']:.3f}  acc={b['accuracy']:.3f}")
    print(f"weekly rolling  : sharpe={r['sharpe']:>5}  auc={r['auc']:.3f}  acc={r['accuracy']:.3f}  "
          f"({r['weeks']} weeks, hit {r['hitRate'] * 100:.0f}%)")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "rolling_window.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
