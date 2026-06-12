"""
Which feature families actually earn their place?

SHAP says which features the model leans on; ablation says which ones it would
miss. Drop one group at a time, refit on the identical walk-forward folds, and
watch what happens to OOS Sharpe and AUC. A group whose removal barely moves the
needle is carrying its weight in name only. The second half does the opposite -
bolts the inferred earnings-cycle features on and measures whether they add
anything, which is the honest way to decide if a new feature is worth shipping.

    python -m ml.research.ablation

Writes data/research/ablation.json.
"""
from __future__ import annotations

import json

import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.features.earnings import EARNINGS_FEATURES, attach_earnings
from ml.labels.outperformance import make_labels
from ml.training.walk_forward import classification_metrics, strategy_metrics, walk_forward

# the 24 features, grouped the way features/build.py lays them out
FEATURE_GROUPS: dict[str, list[str]] = {
    "Momentum": ["ret_5", "ret_20", "ret_60", "ret_120"],
    "Trend": ["sma20_dist", "sma50_dist", "sma200_dist"],
    "Oscillators": ["rsi_14", "bb_pctb", "macd_hist"],
    "Volatility": ["vol_20", "vol_60", "vol_of_vol", "atr_pct"],
    "Volume": ["volume_z", "dollar_vol_z", "obv_slope"],
    "Range/Extremes": ["dist_52w_high", "dist_52w_low", "ret_skew_20", "ret_kurt_20"],
    "Microstructure": ["gap", "intraday_range"],
    "Relative": ["rel_strength_20"],
}


def _score(d: pd.DataFrame, cols: list[str]) -> dict:
    oos = walk_forward(d, feature_cols=cols, verbose=False)
    return {**strategy_metrics(oos), **classification_metrics(oos)}


def run_ablation(d: pd.DataFrame) -> dict:
    """Leave-one-group-out, measured against the full-feature baseline."""
    base = _score(d, FEATURE_COLS)
    print(f"  full ({len(FEATURE_COLS)} feats)        sharpe={base['sharpe']:>5}  auc={base['auc']:.3f}")
    rows = []
    for group, cols in FEATURE_GROUPS.items():
        kept = [c for c in FEATURE_COLS if c not in cols]
        s = _score(d, kept)
        row = {
            "group": group,
            "nDropped": len(cols),
            "sharpeWithout": s["sharpe"],
            "aucWithout": s["auc"],
            "sharpeDelta": round(s["sharpe"] - base["sharpe"], 3),
            "aucDelta": round(s["auc"] - base["auc"], 4),
        }
        rows.append(row)
        print(f"  -{group:18} sharpe={s['sharpe']:>5} ({row['sharpeDelta']:+.2f})  "
              f"auc={s['auc']:.3f} ({row['aucDelta']:+.3f})")
    # most important = biggest drop when removed
    rows.sort(key=lambda r: r["sharpeDelta"])
    return {"baseline": base, "groups": rows}


def earnings_experiment(features: pd.DataFrame, ohlcv: pd.DataFrame) -> dict:
    """Does the inferred earnings-cycle group add anything over the 24 features?"""
    d_base = make_labels(features)
    base = _score(d_base, FEATURE_COLS)

    ext = attach_earnings(features, ohlcv)
    d_ext = make_labels(ext)
    with_earn = _score(d_ext, FEATURE_COLS + EARNINGS_FEATURES)

    delta = round(with_earn["sharpe"] - base["sharpe"], 3)
    verdict = (
        f"24 features Sharpe {base['sharpe']} -> +earnings {with_earn['sharpe']} "
        f"({delta:+}). "
        + ("Worth promoting." if delta >= 0.05 else
           "No real lift - kept out of the production model, reported honestly.")
    )
    print(f"\n  earnings experiment: {verdict}")
    return {
        "baseSharpe": base["sharpe"], "baseAuc": base["auc"],
        "withEarningsSharpe": with_earn["sharpe"], "withEarningsAuc": with_earn["auc"],
        "sharpeDelta": delta,
        "features": EARNINGS_FEATURES,
        "verdict": verdict,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("Run `python -m ml.features.build` first.")
    feats = pd.read_parquet(paths.FEATURES_PATH)
    d = make_labels(feats)
    print(f"Feature ablation on {len(d):,} rows · same {6}-fold walk-forward\n")
    ablation = run_ablation(d)

    earn = None
    if paths.OHLCV_PATH.exists():
        ohlcv = pd.read_parquet(paths.OHLCV_PATH)
        earn = earnings_experiment(feats, ohlcv)

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "ablation.json"
    out_path.write_text(json.dumps({
        "note": "Leave-one-group-out vs the full 24-feature model, identical folds. "
                "Signal-quality (frictionless) metrics.",
        "ablation": ablation,
        "earningsExperiment": earn,
    }, indent=2))
    print(f"\nSaved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
