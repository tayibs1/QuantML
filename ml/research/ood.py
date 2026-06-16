"""
Out-of-distribution test: train on the past, evaluate on a new regime.

Walk-forward tests gradual drift. This tests a hard break: freeze a model on
2018-2022 and turn it loose, untouched, on 2023 onward — the rate-hike / AI-boom
regime it never saw. Live trading does exactly this between retrains, so a model
that holds up here is one you can trust to degrade gracefully rather than fall off
a cliff.

We also quantify *how* different the test era is, per feature, with the same PSI used
for live drift monitoring — so the result comes with a measure of how hard the test
actually was, not just a pass/fail.

    python -m ml.research.ood

Reads data/processed/features.parquet, writes data/research/ood.json.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS, FEATURE_LABELS
from ml.labels.outperformance import make_labels
from ml.research.drift import ALERT, WARN, psi
from ml.training.walk_forward import _new_model, classification_metrics, strategy_metrics

TRAIN_END = "2023-01-01"  # train strictly before this, test on/after


def ood_split(d: pd.DataFrame, train_end: str = TRAIN_END) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = pd.Timestamp(train_end)
    return d[d["date"] < cut], d[d["date"] >= cut]


def era_drift(train: pd.DataFrame, test: pd.DataFrame, cols: list[str]) -> list[dict]:
    rows = []
    for c in cols:
        if c not in train.columns:
            continue
        p = round(psi(train[c], test[c]), 4)
        status = "ALERT" if p >= ALERT else ("WARN" if p >= WARN else "OK")
        rows.append({"feature": c, "label": FEATURE_LABELS.get(c, c), "psi": p, "status": status})
    rows.sort(key=lambda r: r["psi"], reverse=True)
    return rows


def evaluate(
    d: pd.DataFrame,
    train_end: str = TRAIN_END,
    model_factory=_new_model,
    feature_cols: list[str] | None = None,
) -> dict:
    cols = feature_cols or FEATURE_COLS
    train, test = ood_split(d, train_end)
    model = model_factory().fit(train[cols], train["label"])

    proba = model.predict_proba(test[cols])
    oos = test[["date", "ticker", "fwd_ret_5", "label"]].copy()
    oos["pred"] = proba.argmax(1)
    oos["p_avoid"], oos["p_hold"], oos["p_buy"] = proba[:, 0], proba[:, 1], proba[:, 2]

    metrics = {**classification_metrics(oos), **strategy_metrics(oos)}
    drift = era_drift(train, test, cols)
    return {
        "trainEnd": train_end,
        "trainRows": int(len(train)),
        "testRows": int(len(test)),
        "metrics": metrics,
        "eraDrift": drift,
        "overallDrift": drift[0]["status"] if drift else "OK",
    }


def run() -> dict:
    d = make_labels(pd.read_parquet(paths.FEATURES_PATH))
    result = evaluate(d)
    result["note"] = (
        "Trained on data before 2023 and frozen; evaluated untouched on 2023+. "
        "eraDrift is per-feature PSI between the two eras (how hard the test was)."
    )
    result["generatedAt"] = date.today().isoformat()
    return result


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    result = run()
    m = result["metrics"]
    print(f"train < {result['trainEnd']} ({result['trainRows']:,} rows) -> "
          f"test ({result['testRows']:,} rows)")
    print(f"OOD  sharpe={m['sharpe']}  auc={m['auc']:.3f}  acc={m['accuracy']:.3f}  "
          f"era-drift {result['overallDrift']}")
    for r in result["eraDrift"][:5]:
        print(f"  {r['feature']:<16} psi={r['psi']:.3f}  {r['status']}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "ood.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
