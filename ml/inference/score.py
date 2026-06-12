"""
Stage 4: inference.

Load the trained model, score the latest cross-section, write signals in the
shape the frontend/backend already expect. This is the only thing the ML side
publishes for live use, and it only ever emits signals - never orders.

    python -m ml.inference.score

Writes:
    data/signals/latest.json   Signal[]  (matches backend/schemas.py::Signal)
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from ml import paths
from ml.features.build import FEATURE_COLS, FEATURE_LABELS, compute_features
from ml.universe import company, sector

TOP_DRIVERS = 3


def _finite(x, default: float = 0.0) -> float:
    """Force to a JSON-safe float; NaN/inf fall back to default."""
    try:
        x = float(x)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _risk_levels(ohlcv: pd.DataFrame, asof: pd.Timestamp) -> dict[str, str]:
    """Bucket each name by where its realised vol sits in the universe."""
    px = ohlcv[ohlcv["date"] <= asof].sort_values(["ticker", "date"])
    vol = (
        px.groupby("ticker")["close"]
        .apply(lambda s: s.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252))
    )
    vol = vol.dropna()
    if vol.empty:
        return {}
    pct = vol.rank(pct=True)
    out = {}
    for t, p in pct.items():
        out[t] = ("Low" if p < 0.4 else "Moderate" if p < 0.7 else "High" if p < 0.9 else "Elevated")
    return out


def _drivers(model: xgb.XGBClassifier, X: pd.DataFrame, pred_class: np.ndarray) -> list[list[str]]:
    """Top features by |contribution| per row, for its predicted class.

    Uses xgboost's native pred_contribs (SHAP values) rather than pulling in the
    shap package - saves a heavy dependency for the same numbers.
    """
    n, nfeat = X.shape
    try:
        booster = model.get_booster()
        dmat = xgb.DMatrix(X.values, feature_names=list(X.columns))
        contribs = booster.predict(dmat, pred_contribs=True)
        contribs = np.asarray(contribs).reshape(n, 3, nfeat + 1)  # rows x classes x (feats+bias)
        result = []
        for i in range(n):
            row = np.abs(contribs[i, int(pred_class[i]), :nfeat])
            top = np.argsort(row)[::-1][:TOP_DRIVERS]
            result.append([FEATURE_LABELS[FEATURE_COLS[j]] for j in top])
        return result
    except Exception:
        # if contribs blow up, fall back to global gain importance (every row
        # then shows the same drivers, but at least it doesn't crash)
        imp = pd.Series(model.feature_importances_, index=FEATURE_COLS)
        top = imp.sort_values(ascending=False).head(TOP_DRIVERS).index
        labels = [FEATURE_LABELS[f] for f in top]
        return [labels for _ in range(n)]


def score() -> list[dict]:
    model_path = paths.MODELS_DIR / "xgb_signal.joblib"
    if not model_path.exists():
        raise SystemExit("No model. Run `python -m ml.training.walk_forward` first.")
    if not paths.OHLCV_PATH.exists():
        raise SystemExit("No data. Run `python -m ml.ingestion.download` first.")

    model: xgb.XGBClassifier = joblib.load(model_path)
    meta = json.loads(paths.MODEL_META_PATH.read_text())
    class_to_signal = {int(k): v for k, v in meta["class_to_signal"].items()}
    class_mean_fwd = {int(k): v for k, v in meta["class_mean_fwd_ret"].items()}

    ohlcv = pd.read_parquet(paths.OHLCV_PATH)
    feats = compute_features(ohlcv)
    asof = feats["date"].max()
    latest = feats[feats["date"] == asof].reset_index(drop=True)

    X = latest[FEATURE_COLS]
    proba = model.predict_proba(X)
    pred = proba.argmax(1)
    conf = proba.max(1) * 100
    exp_ret = (proba * np.array([class_mean_fwd[c] for c in range(3)])).sum(1) * 100
    drivers = _drivers(model, X, pred)
    risk = _risk_levels(ohlcv, asof)

    # latest price and 1d change per ticker, both ticker-indexed so they line up
    recent = ohlcv[ohlcv["date"] <= asof].sort_values(["ticker", "date"])
    grp = recent.groupby("ticker")["close"]
    last_close = grp.last()
    prev_close = grp.apply(lambda s: s.iloc[-2] if len(s) >= 2 else float("nan"))
    change = (last_close / prev_close - 1) * 100

    signals = []
    for i, row in latest.iterrows():
        t = row["ticker"]
        signals.append(
            {
                "ticker": t,
                "company": company(t),
                "signal": class_to_signal[int(pred[i])],
                "confidence": round(_finite(conf[i]), 1),
                "expectedReturn5d": round(_finite(exp_ret[i]), 2),
                "risk": risk.get(t, "Moderate"),
                "model": meta.get("model_name", "XGBoost-v3"),
                "drivers": drivers[i],
                "price": round(_finite(last_close.get(t, row.get("close", 0.0))), 2),
                "change": round(_finite(change.get(t, 0.0)), 2),
                "sector": sector(t),
            }
        )

    # order BUY (highest conf first) then HOLD then AVOID
    order = {"BUY": 0, "HOLD": 1, "AVOID": 2}
    signals.sort(key=lambda s: (order[s["signal"]], -s["confidence"]))
    return signals


def main() -> None:
    paths.ensure_dirs()
    signals = score()
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals,
    }
    paths.SIGNALS_PATH.write_text(json.dumps(payload, indent=2))
    n_buy = sum(s["signal"] == "BUY" for s in signals)
    n_hold = sum(s["signal"] == "HOLD" for s in signals)
    n_avoid = sum(s["signal"] == "AVOID" for s in signals)
    print(f"Scored {len(signals)} names → BUY {n_buy} · HOLD {n_hold} · AVOID {n_avoid}")
    print(f"Saved {paths.SIGNALS_PATH.relative_to(paths.REPO_ROOT)}")
    for s in signals[:8]:
        print(f"  {s['ticker']:5} {s['signal']:5} {s['confidence']:5.1f}%  "
              f"exp5d={s['expectedReturn5d']:+.2f}%  [{', '.join(s['drivers'])}]")


if __name__ == "__main__":
    main()
