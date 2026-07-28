"""
Stage 4b: save the per-name SHAP breakdown.

Scoring already works out how much each feature pushed a prediction, but it only
keeps the top three names and throws the numbers away. The research assistant
needs the actual numbers, and it needs the sign: a feature that pushed the call
*towards* BUY reads very differently from one that pushed against it.

So this re-runs the same attribution and writes all of it to disk.

    python -m ml.inference.shap_summary

Writes:
    data/research/shap/latest.json
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from ml import paths
from ml.features.build import FEATURE_COLS, FEATURE_LABELS, compute_features

SHAP_DIR = paths.RESEARCH_DIR / "shap"

# Keep every feature for the top-level file but mark the ones worth showing.
TOP_N = 6


def _safe(x: float, default: float = 0.0) -> float:
    """JSON can't hold NaN or infinity, so swap those for a harmless number."""
    x = float(x)
    return x if np.isfinite(x) else default


def contributions(
    model: xgb.XGBClassifier, X: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """How much each feature moved each prediction, per row and per class.

    XGBoost can hand back these numbers itself (they're SHAP values), which
    saves pulling in the separate shap package for the same result. The last
    column it returns is the model's starting point rather than a feature, so
    it gets split off and returned separately.

    Returns (contribs, base) shaped (rows, classes, features) and (rows, classes).
    """
    n, n_feat = X.shape
    booster = model.get_booster()
    dmat = xgb.DMatrix(X.values, feature_names=list(X.columns))
    raw = np.asarray(booster.predict(dmat, pred_contribs=True))
    raw = raw.reshape(n, -1, n_feat + 1)
    return raw[:, :, :n_feat], raw[:, :, n_feat]


def build() -> dict:
    model_path = paths.MODELS_DIR / "xgb_signal.joblib"
    if not model_path.exists():
        raise SystemExit("No model. Run `python -m ml.training.walk_forward` first.")
    if not paths.OHLCV_PATH.exists():
        raise SystemExit("No data. Run `python -m ml.ingestion.download` first.")

    model: xgb.XGBClassifier = joblib.load(model_path)
    meta = json.loads(paths.MODEL_META_PATH.read_text())
    class_to_signal = {int(k): v for k, v in meta["class_to_signal"].items()}

    ohlcv = pd.read_parquet(paths.OHLCV_PATH)
    feats = compute_features(ohlcv)
    asof = feats["date"].max()
    latest = feats[feats["date"] == asof].reset_index(drop=True)

    X = latest[FEATURE_COLS]
    proba = model.predict_proba(X)
    pred = proba.argmax(1)
    contribs, base = contributions(model, X)

    tickers: dict[str, dict] = {}
    for i, ticker in enumerate(latest["ticker"]):
        cls = int(pred[i])
        row = contribs[i, cls]
        # biggest movers first, regardless of which way they pushed
        order = np.argsort(np.abs(row))[::-1]
        drivers = [
            {
                "key": FEATURE_COLS[j],
                "label": FEATURE_LABELS[FEATURE_COLS[j]],
                "contribution": round(_safe(row[j]), 5),
                "direction": "supports" if row[j] >= 0 else "opposes",
                "featureValue": round(_safe(X.iloc[i, j]), 4),
            }
            for j in order
        ]
        tickers[str(ticker)] = {
            "signal": class_to_signal[cls],
            "predictedClass": cls,
            "confidence": round(_safe(proba[i, cls] * 100), 1),
            "baseValue": round(_safe(base[i, cls]), 5),
            "drivers": drivers,
        }

    return {
        "generatedAt": datetime.now(UTC).isoformat(),
        "asOf": str(pd.Timestamp(asof).date()),
        "model": meta.get("model_name", "XGBoost-v3"),
        "method": "XGBoost native pred_contribs (TreeSHAP), margin space, predicted class",
        "topN": TOP_N,
        "featureCount": len(FEATURE_COLS),
        "tickers": tickers,
    }


def main() -> None:
    payload = build()
    SHAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SHAP_DIR / "latest.json"
    out.write_text(json.dumps(payload, indent=2))

    n = len(payload["tickers"])
    print(f"SHAP breakdown for {n} names → {out.relative_to(paths.REPO_ROOT)}")
    for ticker, row in list(payload["tickers"].items())[:5]:
        top = row["drivers"][0]
        arrow = "+" if top["direction"] == "supports" else "-"
        print(f"  {ticker:5} {row['signal']:5} top={top['label']} ({arrow}{abs(top['contribution']):.3f})")


if __name__ == "__main__":
    main()
