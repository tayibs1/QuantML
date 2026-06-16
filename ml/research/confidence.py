"""
Confidence-weighted sizing and probability calibration.

The model outputs a probability per class, not just a label — so two questions worth
asking before trusting it with size:

1. Does sizing BUY positions by conviction (p_buy) beat equal-weighting them? Traders
   don't put full size on a coin-flip; if the probabilities carry information, leaning
   into the high-conviction names should improve risk-adjusted return.
2. Are the probabilities *calibrated*? When the model says 60%, does a BUY actually land
   in the top tercile ~60% of the time? A model can rank well yet be badly calibrated,
   and you can't size by a number you can't trust. We measure it with a reliability curve
   and the Brier score.

    python -m ml.research.confidence

Reads features, writes data/research/confidence.json.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from ml import paths
from ml.labels.outperformance import BUY, make_labels
from ml.training.walk_forward import _new_model, walk_forward

PERIODS_PER_YEAR = 252 / 5
N_BINS = 10


def _metrics_from_basket(daily: pd.Series) -> dict:
    """Sharpe/CAGR/maxDD from a daily basket return series, de-overlapped to 5 days."""
    r = daily.sort_index().iloc[::5]
    if len(r) < 3 or r.std(ddof=1) == 0:
        return {"sharpe": 0.0, "cagr": 0.0, "maxDrawdown": 0.0}
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))
    equity = (1 + r).cumprod()
    years = len(r) / PERIODS_PER_YEAR
    return {
        "sharpe": round(sharpe, 2),
        "cagr": round(float(equity.iloc[-1] ** (1 / years) - 1), 4),
        "maxDrawdown": round(float((equity / equity.cummax() - 1).min()), 4),
    }


def sizing_comparison(oos: pd.DataFrame) -> dict:
    """Equal-weight vs p_buy-weighted BUY basket."""
    buy = oos[oos["pred"] == BUY]
    if buy.empty:
        return {"equalWeight": {}, "confidenceWeighted": {}}

    equal = buy.groupby("date")["fwd_ret_5"].mean()
    weighted = buy.groupby("date").apply(
        lambda g: float(np.average(g["fwd_ret_5"], weights=g["p_buy"])), include_groups=False
    )
    return {
        "equalWeight": _metrics_from_basket(equal),
        "confidenceWeighted": _metrics_from_basket(weighted),
    }


def calibration(oos: pd.DataFrame, n_bins: int = N_BINS) -> dict:
    """Reliability curve + Brier score for the BUY probability (one-vs-rest)."""
    p = oos["p_buy"].to_numpy()
    y = (oos["label"] == BUY).astype(int).to_numpy()
    brier = float(np.mean((p - y) ** 2))

    df = pd.DataFrame({"p": p, "y": y})
    df["bin"] = pd.qcut(df["p"], n_bins, duplicates="drop")
    bins = []
    for _, g in df.groupby("bin", observed=True):
        bins.append({
            "pMean": round(float(g["p"].mean()), 4),
            "observed": round(float(g["y"].mean()), 4),
            "n": int(len(g)),
        })
    # expected calibration error: avg gap between predicted and observed, n-weighted
    total = sum(b["n"] for b in bins) or 1
    ece = sum(abs(b["pMean"] - b["observed"]) * b["n"] for b in bins) / total
    return {"brier": round(brier, 4), "ece": round(ece, 4), "bins": bins}


def run() -> dict:
    d = make_labels(pd.read_parquet(paths.FEATURES_PATH))
    oos = walk_forward(d, model_factory=_new_model, verbose=False)
    sizing = sizing_comparison(oos)
    calib = calibration(oos)

    eq, cw = sizing["equalWeight"], sizing["confidenceWeighted"]
    improves = cw.get("sharpe", 0) > eq.get("sharpe", 0)
    return {
        "note": "Equal-weight vs conviction-weighted BUY basket, plus BUY-probability "
                "calibration (reliability curve + Brier). Frictionless, OOS.",
        "generatedAt": date.today().isoformat(),
        "sizing": sizing,
        "confidenceImprovesSharpe": improves,
        "calibration": calib,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    result = run()
    eq, cw = result["sizing"]["equalWeight"], result["sizing"]["confidenceWeighted"]
    print(f"equal-weight   sharpe={eq['sharpe']}  maxDD={eq['maxDrawdown']}")
    print(f"conf-weighted  sharpe={cw['sharpe']}  maxDD={cw['maxDrawdown']}  "
          f"({'better' if result['confidenceImprovesSharpe'] else 'no improvement'})")
    print(f"calibration    Brier={result['calibration']['brier']}  ECE={result['calibration']['ece']}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "confidence.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
