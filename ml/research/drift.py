"""
Feature drift monitoring (Population Stability Index).

A model only keeps its edge while the world looks like its training data. This
compares each feature's recent distribution against its historical reference
distribution and flags the ones that have moved. PSI is the standard credit-risk
metric for exactly this:

    PSI < 0.10  → OK     (no material shift)
    0.10–0.25   → WARN   (moderate shift, watch it)
    PSI > 0.25  → ALERT  (major shift, the model may be operating out-of-domain)

    python -m ml.research.drift

Reads data/processed/features.parquet, writes data/research/drift.json so the API
can surface a live "is the model still in-domain?" signal on the dashboard.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS, FEATURE_LABELS

RECENT_DAYS = 5  # the latest cross-sections we treat as "current"
WARN, ALERT = 0.10, 0.25


def psi(reference, current, bins: int = 10, eps: float = 1e-6) -> float:
    """Population Stability Index between two samples, using reference deciles."""
    ref = np.asarray(reference, dtype="float64")
    cur = np.asarray(current, dtype="float64")
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]
    if len(ref) < bins or len(cur) == 0:
        return 0.0

    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:  # degenerate / near-constant feature
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    ref_pct = np.histogram(ref, edges)[0] / len(ref)
    cur_pct = np.histogram(cur, edges)[0] / len(cur)
    ref_pct = np.clip(ref_pct, eps, None)
    cur_pct = np.clip(cur_pct, eps, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def _status(p: float) -> str:
    if p >= ALERT:
        return "ALERT"
    if p >= WARN:
        return "WARN"
    return "OK"


def feature_drift(
    features: pd.DataFrame,
    recent_days: int = RECENT_DAYS,
    feature_cols: list[str] | None = None,
) -> dict:
    """Per-feature PSI of the last `recent_days` cross-sections vs the rest."""
    cols = feature_cols or FEATURE_COLS
    f = features.sort_values("date")
    dates = np.array(sorted(f["date"].unique()))
    recent_days = max(1, min(recent_days, len(dates) - 1))
    recent = set(dates[-recent_days:])

    cur = f[f["date"].isin(recent)]
    ref = f[~f["date"].isin(recent)]

    rows = []
    for col in cols:
        if col not in f.columns:
            continue
        p = round(psi(ref[col], cur[col]), 4)
        rows.append({
            "feature": col,
            "label": FEATURE_LABELS.get(col, col),
            "psi": p,
            "status": _status(p),
        })
    rows.sort(key=lambda r: r["psi"], reverse=True)

    if any(r["status"] == "ALERT" for r in rows):
        overall = "ALERT"
    elif any(r["status"] == "WARN" for r in rows):
        overall = "WARN"
    else:
        overall = "OK"

    return {
        "recentDays": recent_days,
        "referenceDates": int(len(dates) - recent_days),
        "overall": overall,
        "features": rows,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    feats = pd.read_parquet(paths.FEATURES_PATH)
    result = feature_drift(feats)
    result["note"] = (
        "PSI of the latest cross-sections vs the historical reference window. "
        "OK<0.10, WARN<0.25, ALERT>=0.25."
    )
    result["generatedAt"] = date.today().isoformat()

    print(f"Feature drift — overall: {result['overall']}  (recent {result['recentDays']} days)")
    for r in result["features"][:6]:
        print(f"  {r['feature']:<16} psi={r['psi']:.4f}  {r['status']}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "drift.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
