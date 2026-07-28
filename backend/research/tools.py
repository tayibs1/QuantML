"""
Exact lookups.

Search finds text that is probably relevant. That is the wrong tool for "what is
NVDA's confidence", where being approximately right is the same as being wrong.
These functions read the artifacts directly and return the actual figures.

Everything a QuantML answer states as a number should come from here. The search
results explain and contextualise; these supply the facts. Keeping the two apart
is what stops a plausible-sounding wrong number reaching the user.

Every function returns a dict with an `ok` flag. Missing data is a normal answer,
not an error, because "the pipeline hasn't produced that yet" is something the
assistant should be able to say.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from config import settings

CORPUS_DIR = Path(__file__).parent / "corpus"

# Feature names get typed loosely. "momentum_20d" and "20-day momentum" should
# both find ret_20.
FEATURE_ALIASES = {
    "momentum_20d": "ret_20",
    "momentum_5d": "ret_5",
    "momentum_60d": "ret_60",
    "momentum_120d": "ret_120",
    "rsi": "rsi_14",
    "macd": "macd_hist",
    "atr": "atr_pct",
    "volume": "volume_z",
    "bollinger": "bb_pctb",
    "obv": "obv_slope",
    "rel_strength": "rel_strength_20",
    "relative_strength": "rel_strength_20",
    "volatility": "vol_20",
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return None


def _missing(what: str, where: str) -> dict:
    return {
        "ok": False,
        "reason": f"No {what} available. Expected it at {where}; "
                  f"run the pipeline to generate it.",
    }


# --- signals ------------------------------------------------------------------

def get_latest_signal(ticker: str) -> dict:
    """The current signal for one name, exactly as the model emitted it."""
    payload = _read_json(settings.signals_dir / "latest.json")
    if not payload or not payload.get("signals"):
        return _missing("signal data", "data/signals/latest.json")

    want = (ticker or "").upper().strip()
    match = next((s for s in payload["signals"] if s["ticker"].upper() == want), None)
    if match is None:
        known = sorted(s["ticker"] for s in payload["signals"])
        return {
            "ok": False,
            "reason": f"{want} is not in the scored universe.",
            "universe": known,
        }

    return {
        "ok": True,
        "ticker": match["ticker"],
        "company": match.get("company"),
        "sector": match.get("sector"),
        "signal": match["signal"],
        "confidence": match.get("confidence"),
        "expectedReturn5d": match.get("expectedReturn5d"),
        "risk": match.get("risk"),
        "model": match.get("model"),
        "price": match.get("price"),
        "change": match.get("change"),
        "drivers": match.get("drivers", []),
        "generatedAt": payload.get("generatedAt"),
        "source_path": "data/signals/latest.json",
        # three balanced classes, so this is the level that means "no opinion"
        "chanceLevel": 33.3,
    }


def get_signal_distribution() -> dict:
    """How the whole universe is currently split across the three labels."""
    payload = _read_json(settings.signals_dir / "latest.json")
    if not payload or not payload.get("signals"):
        return _missing("signal data", "data/signals/latest.json")
    signals = payload["signals"]
    counts = {k: sum(1 for s in signals if s["signal"] == k)
              for k in ("BUY", "HOLD", "AVOID")}
    return {
        "ok": True,
        "counts": counts,
        "total": len(signals),
        "generatedAt": payload.get("generatedAt"),
        "source_path": "data/signals/latest.json",
    }


# --- attribution --------------------------------------------------------------

def get_top_shap_drivers(ticker: str, limit: int = 6) -> dict:
    """Which features moved this prediction, and which way they pushed."""
    payload = _read_json(settings.data_dir / "research" / "shap" / "latest.json")
    if not payload or not payload.get("tickers"):
        return _missing(
            "feature attribution", "data/research/shap/latest.json"
        )

    want = (ticker or "").upper().strip()
    row = payload["tickers"].get(want)
    if row is None:
        return {"ok": False, "reason": f"No attribution recorded for {want}."}

    drivers = row.get("drivers", [])
    supporting = [d for d in drivers if d["direction"] == "supports"][:limit]
    opposing = [d for d in drivers if d["direction"] == "opposes"][:limit]

    return {
        "ok": True,
        "ticker": want,
        "signal": row.get("signal"),
        "confidence": row.get("confidence"),
        "baseValue": row.get("baseValue"),
        "supporting": supporting,
        "opposing": opposing,
        "asOf": payload.get("asOf"),
        "model": payload.get("model"),
        "method": payload.get("method"),
        "source_path": "data/research/shap/latest.json",
    }


# --- model / validation -------------------------------------------------------

def get_model_metrics(model_version: str | None = None) -> dict:
    """Out-of-sample metrics for the champion, or a named model."""
    card = _read_json(settings.models_dir / "model_card.json")
    meta = _read_json(settings.models_dir / "xgb_signal.meta.json")
    if not card and not meta:
        return _missing("model metrics", "data/models/model_card.json")

    models = (card or {}).get("models", [])
    chosen = None
    if model_version:
        chosen = next(
            (m for m in models if str(m.get("name", "")).lower() == model_version.lower()),
            None,
        )
    if chosen is None:
        chosen = next((m for m in models if m.get("status") == "Champion"), None)
    if chosen is None and models:
        chosen = models[0]

    out = {
        "ok": True,
        "source_path": "data/models/model_card.json",
        # what these numbers look like when the model knows nothing
        "baselines": {"accuracy": 33.3, "auc": 0.50},
    }
    if chosen:
        out.update({
            "model": chosen.get("name"),
            "status": chosen.get("status"),
            "auc": chosen.get("auc"),
            "accuracy": chosen.get("accuracy"),
            "sharpe": chosen.get("sharpe"),
            "cagr": chosen.get("cagr"),
            "maxDrawdown": chosen.get("maxDrawdown"),
            "validation": chosen.get("validation"),
            "trainingWindow": chosen.get("trainingWindow"),
            "features": chosen.get("features"),
            "drift": chosen.get("drift"),
            "lastTrained": chosen.get("lastTrained"),
        })
    if meta:
        out["training"] = {
            "labelMethod": meta.get("label_method"),
            "horizonDays": meta.get("horizon_days"),
            "trainStart": meta.get("train_start"),
            "trainEnd": meta.get("train_end"),
            "metrics": meta.get("metrics", {}),
            "classToSignal": meta.get("class_to_signal"),
        }
    return out


def get_backtest_summary(ticker: str | None = None, model_version: str | None = None) -> dict:
    """Net-of-cost walk-forward performance, and this name's trades if asked."""
    bt = _read_json(settings.data_dir / "backtests" / "latest.json")
    if not bt:
        return _missing("backtest results", "data/backtests/latest.json")

    metrics = bt.get("metrics", {})
    config = bt.get("config", {})
    out = {
        "ok": True,
        "window": bt.get("window", {}),
        "config": config,
        "metrics": {
            k: metrics.get(k) for k in (
                "cagr", "totalReturn", "sharpe", "sortino", "volatility",
                "maxDrawdown", "benchTotalReturn", "benchCagr", "beta",
                "benchCorrelation", "excessReturn",
            ) if metrics.get(k) is not None
        },
        "tradeCount": bt.get("tradeCount"),
        "costsBps": {
            "commission": config.get("commission_bps"),
            "slippage": config.get("slippage_bps"),
            "roundTrip": (config.get("commission_bps", 0) or 0)
                         + (config.get("slippage_bps", 0) or 0),
        },
        "netOfCosts": True,
        "generatedAt": bt.get("generatedAt"),
        "source_path": "data/backtests/latest.json",
    }
    if model_version:
        out["requestedModel"] = model_version
        out["configModel"] = config.get("model")

    if ticker:
        want = ticker.upper().strip()
        rows = [t for t in bt.get("trades", []) if t.get("ticker", "").upper() == want]
        if rows:
            wins = sum(1 for t in rows if (t.get("ret") or 0) > 0)
            out["tickerTrades"] = {
                "ticker": want,
                "count": len(rows),
                "winRate": round(100 * wins / len(rows), 1),
                "avgReturn": round(sum(t.get("ret", 0) for t in rows) / len(rows), 3),
                "avgHoldDays": round(sum(t.get("hold", 0) for t in rows) / len(rows), 1),
                "recent": rows[:5],
            }
        else:
            out["tickerTrades"] = {
                "ticker": want,
                "count": 0,
                "note": f"{want} has no closed trades in the backtest ledger. "
                        f"The ledger holds a sample of closed trades, so absence "
                        f"is not proof the name was never held.",
            }
    return out


# --- risk ---------------------------------------------------------------------

def get_risk_summary(ticker: str) -> dict:
    """What the risk layer does with this signal, and the limits it works under.

    This is where the raw signal and the actual position part company: a strong
    BUY on a volatile name can end up smaller than a modest BUY on a calm one.
    """
    from portfolio.risk_engine import RISK_FACTOR, RiskParams, propose_orders

    payload = _read_json(settings.signals_dir / "latest.json")
    if not payload or not payload.get("signals"):
        return _missing("signal data", "data/signals/latest.json")

    want = (ticker or "").upper().strip()
    signals = payload["signals"]
    match = next((s for s in signals if s["ticker"].upper() == want), None)
    if match is None:
        return {"ok": False, "reason": f"{want} is not in the scored universe."}

    params = RiskParams()
    proposed = propose_orders(signals)["orders"]
    order = next((o for o in proposed if o.ticker.upper() == want), None)

    risk_level = match.get("risk", "Moderate")
    out = {
        "ok": True,
        "ticker": want,
        "signalRiskLevel": risk_level,
        "riskLevelMeaning": "Volatility rank within the universe only. It excludes "
                            "earnings dates, company news, liquidity and crowding.",
        "volatilitySizingFactor": RISK_FACTOR.get(risk_level, 0.7),
        "limits": {
            "maxNameWeight": params.max_name_weight,
            "maxSectorWeight": params.max_sector_weight,
            "grossTarget": params.gross_target,
            "maxPositions": params.max_positions,
            "longOnly": True,
        },
        "inProposedBook": order is not None,
        "source_path": "backend/portfolio/risk_engine.py",
    }
    if order is not None:
        out["proposedWeight"] = round(getattr(order, "weight", 0.0), 4)
        out["atNameCap"] = round(getattr(order, "weight", 0.0), 4) >= params.max_name_weight
    elif match["signal"] != "BUY":
        out["note"] = (
            f"The book is long-only, so a {match['signal']} signal produces no "
            f"position rather than a short."
        )
    else:
        out["note"] = (
            "BUY signal, but it did not make the proposed book — it ranked below "
            "the position limit or was scaled out by a sector cap."
        )
    return out


# --- feature definitions ------------------------------------------------------

@lru_cache(maxsize=1)
def _feature_sections() -> dict[str, dict]:
    """Parse the feature dictionary into one entry per feature.

    The dictionary is a markdown document rather than a data structure because
    it is also indexed for search and read by humans. Parsing it here keeps one
    copy of the truth instead of two that drift apart.
    """
    path = CORPUS_DIR / "feature_dictionary.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    sections: dict[str, dict] = {}
    # headings look like: "## ret_20 — 20-day momentum"
    pattern = re.compile(r"^##\s+([a-z0-9_]+)\s*[—-]\s*(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = {
            "key": m.group(1),
            "label": m.group(2).strip(),
            "definition": text[m.end():end].strip(),
        }
    return sections


def get_feature_definition(feature_name: str) -> dict:
    """What a feature is and how it's worked out."""
    sections = _feature_sections()
    if not sections:
        return _missing("feature dictionary", "backend/research/corpus/feature_dictionary.md")

    raw = (feature_name or "").strip().lower()
    key = FEATURE_ALIASES.get(raw, raw)

    entry = sections.get(key)
    if entry is None:
        # try matching on the readable label instead of the key
        entry = next(
            (v for v in sections.values() if raw and raw in v["label"].lower()), None
        )
    if entry is None:
        # last resort: the alias table keyed by substring
        for alias, target in FEATURE_ALIASES.items():
            if raw and alias in raw:
                entry = sections.get(target)
                break
    if entry is None:
        return {
            "ok": False,
            "reason": f"'{feature_name}' is not one of the model's features.",
            "available": sorted(sections),
        }

    return {
        "ok": True,
        "key": entry["key"],
        "label": entry["label"],
        "definition": entry["definition"],
        "note": "Every feature is scored against the rest of the universe on the "
                "same day and capped at plus or minus 5, so it is always a "
                "relative measure.",
        "source_path": "backend/research/corpus/feature_dictionary.md",
    }


def list_features() -> dict:
    sections = _feature_sections()
    return {
        "ok": bool(sections),
        "count": len(sections),
        "features": [{"key": k, "label": v["label"]} for k, v in sections.items()],
    }


# Name -> function, so the orchestrator can record what it called by name.
TOOLS = {
    "get_latest_signal": get_latest_signal,
    "get_signal_distribution": get_signal_distribution,
    "get_top_shap_drivers": get_top_shap_drivers,
    "get_model_metrics": get_model_metrics,
    "get_backtest_summary": get_backtest_summary,
    "get_risk_summary": get_risk_summary,
    "get_feature_definition": get_feature_definition,
    "list_features": list_features,
}
