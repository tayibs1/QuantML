"""
Regime-specialised models vs one general model.

The champion loses money in 2022 — a bear year — because it's trained mostly on
bull-market data and learns bull-market habits. The obvious thing to try: train one
model on bull-regime rows, another on bear-regime rows, and route each prediction to
the model that matches the regime in force.

The honest expectation is that this *won't* reliably win: bear regimes are a small
slice of the history, so the bear specialist trains on thin data and is noisy. We
run it on the same expanding folds as the general model, compare overall and in 2022
specifically, and only recommend the ensemble if it actually beats the general model
out-of-sample. If it doesn't, that's the finding, and the general model stays champion.

    python -m ml.research.regime_models

Reads features + benchmark, writes data/research/regime_models.json.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.labels.outperformance import make_labels
from ml.research.regime import benchmark_regime
from ml.training.walk_forward import (
    INITIAL_TRAIN_FRAC,
    N_FOLDS,
    _new_model,
    classification_metrics,
    strategy_metrics,
)

# a regime specialist needs enough rows (and all three classes) or it's just noise;
# below this we fall back to the general model for that regime.
MIN_REGIME_ROWS = 4000


def _predict_block(model, block: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    proba = model.predict_proba(block[cols])
    out = block[["date", "ticker", "fwd_ret_5", "label"]].copy()
    out["pred"] = proba.argmax(1)
    out["p_avoid"], out["p_hold"], out["p_buy"] = proba[:, 0], proba[:, 1], proba[:, 2]
    return out


def _fit_specialist(rows: pd.DataFrame, cols: list[str], model_factory, min_rows: int):
    """A regime model only if there's enough data and all three classes; else None."""
    if len(rows) < min_rows or rows["label"].nunique() < 3:
        return None
    return model_factory().fit(rows[cols], rows["label"])


def regime_walk_forward(
    d: pd.DataFrame,
    model_factory=_new_model,
    feature_cols: list[str] | None = None,
    min_regime_rows: int = MIN_REGIME_ROWS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Expanding folds; returns (general OOS, regime-routed ensemble OOS).

    Expects a 'regime' column on d (Bull/Bear). Each fold trains a general model and
    bull/bear specialists on the same training rows; test rows are routed by their
    own regime, falling back to general where a specialist was too thin to fit.
    """
    cols = feature_cols or FEATURE_COLS
    dates = np.array(sorted(d["date"].unique()))
    n = len(dates)
    start = int(n * INITIAL_TRAIN_FRAC)
    fold = max(1, (n - start) // N_FOLDS)

    gen_rows, ens_rows = [], []
    for k in range(N_FOLDS):
        tr_end = start + k * fold
        te_start = tr_end
        te_end = n if k == N_FOLDS - 1 else tr_end + fold
        if te_start >= n:
            break
        tr = d[d["date"].isin(set(dates[:tr_end]))]
        te = d[d["date"].isin(set(dates[te_start:te_end]))]
        if tr.empty or te.empty:
            continue

        general = model_factory().fit(tr[cols], tr["label"])
        specialists = {
            r: _fit_specialist(tr[tr["regime"] == r], cols, model_factory, min_regime_rows)
            for r in ("Bull", "Bear")
        }

        gen_rows.append(_predict_block(general, te, cols))
        for regime_name, sub in specialists.items():
            block = te[te["regime"] == regime_name]
            if block.empty:
                continue
            ens_rows.append(_predict_block(sub or general, block, cols))

    gen_oos = pd.concat(gen_rows, ignore_index=True) if gen_rows else pd.DataFrame()
    ens_oos = pd.concat(ens_rows, ignore_index=True) if ens_rows else pd.DataFrame()
    return gen_oos, ens_oos


def _year_sharpe(oos: pd.DataFrame, year: int) -> float:
    sub = oos[pd.to_datetime(oos["date"]).dt.year == year]
    return strategy_metrics(sub)["sharpe"] if not sub.empty else 0.0


def run() -> dict:
    feats = pd.read_parquet(paths.FEATURES_PATH)
    if not paths.BENCHMARK_PATH.exists():
        raise SystemExit("Need benchmark.parquet for the regime split.")
    bench = pd.read_parquet(paths.BENCHMARK_PATH)

    d = make_labels(feats)
    regime = benchmark_regime(bench)
    d = d.assign(regime=pd.to_datetime(d["date"]).map(regime).fillna("Bull").values)

    gen_oos, ens_oos = regime_walk_forward(d)
    general = {**classification_metrics(gen_oos), **strategy_metrics(gen_oos)}
    ensemble = {**classification_metrics(ens_oos), **strategy_metrics(ens_oos)}

    beat = ensemble["sharpe"] > general["sharpe"]
    verdict = (
        f"Regime ensemble Sharpe {ensemble['sharpe']} vs general {general['sharpe']} — "
        + ("ensemble wins, worth a closer look."
           if beat else "no improvement; general model stays champion.")
    )
    return {
        "note": "Bull/bear specialists routed by the 200d-SMA regime, same expanding "
                "folds as the general model. Honest test: ship the ensemble only if it wins.",
        "generatedAt": date.today().isoformat(),
        "general": general,
        "ensemble": ensemble,
        "year2022": {"general": _year_sharpe(gen_oos, 2022), "ensemble": _year_sharpe(ens_oos, 2022)},
        "ensembleBeatsGeneral": beat,
        "verdict": verdict,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    result = run()
    g, e = result["general"], result["ensemble"]
    print(f"general  : sharpe={g['sharpe']:>5}  auc={g['auc']:.3f}  (2022 {result['year2022']['general']})")
    print(f"ensemble : sharpe={e['sharpe']:>5}  auc={e['auc']:.3f}  (2022 {result['year2022']['ensemble']})")
    print(result["verdict"])

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "regime_models.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
