"""
Portfolio risk aggregation.

Turns the live signal set into a real risk picture by running it through the
Portfolio/Risk engine (the same `propose_orders` used everywhere else) and
summarising the resulting book: exposure by name and sector, hard-cap usage,
concentration, model conviction, and auto-generated risk flags.

This is read-only and side-effect free. It never executes — it only describes
the *proposed* book. Everything here is derived from real model output when the
ML pipeline has run; it degrades gracefully to sample signals otherwise.
"""
from __future__ import annotations

import statistics
from collections import Counter

from portfolio import RiskParams, propose_orders
from services import store

# Accurate description of what the risk engine actually enforces (see
# portfolio/risk_engine.py). These are policy statements, not generated data.
POSITION_RULES = [
    "Long-only book constructed from BUY signals above the confidence floor.",
    "Per-name exposure hard-capped at 20% of gross.",
    "Per-sector exposure hard-capped at 40% of gross.",
    "Gross exposure capped at 100% — no leverage.",
    "Weights scaled by model confidence and inverse risk level (Low 1.0x to Elevated 0.45x).",
]

_TOP_ASSETS = 8


def _pct(x: float) -> float:
    return round(float(x) * 100, 1)


def _confidence_stats(signals: list[dict]) -> dict:
    confs = [float(s.get("confidence", 0)) for s in signals]
    buys = [float(s["confidence"]) for s in signals if s.get("signal") == "BUY"]
    # Histogram in 10-point buckets across the model's typical range.
    edges = [(0, 40), (40, 50), (50, 60), (60, 70), (70, 100)]
    hist = [
        {"range": f"{lo}-{hi}", "count": sum(1 for c in confs if lo <= c < hi)}
        for lo, hi in edges
    ]
    return {
        "buckets": hist,
        "meanAll": round(statistics.fmean(confs), 1) if confs else 0.0,
        "meanBuy": round(statistics.fmean(buys), 1) if buys else 0.0,
        "nBuy": len(buys),
    }


def _flags(signals, summary, orders, source, conf) -> list[dict]:
    """Generate real, data-driven risk flags from the proposed book."""
    flags: list[dict] = []
    gross = _pct(summary["grossExposure"])
    cash = _pct(summary["cashWeight"])
    sectors = summary.get("exposureBySector", {})

    # 1. Single-name concentration vs the 20% cap.
    if orders:
        top = max(orders, key=lambda o: o.target_weight)
        pct = _pct(top.target_weight)
        flags.append({
            "id": "conc-name",
            "level": "warning" if pct >= 18 else "info",
            "title": "Single-name concentration",
            "detail": f"{top.ticker} is the largest position at {pct:.1f}% of gross (hard cap 20%).",
            "metric": f"{pct:.1f}% / 20%",
        })

    # 2. Sector concentration vs the 40% cap.
    if sectors:
        top_sector, w = max(sectors.items(), key=lambda kv: kv[1])
        pct = _pct(w)
        flags.append({
            "id": "conc-sector",
            "level": "warning" if pct >= 36 else "info",
            "title": "Sector concentration",
            "detail": f"{top_sector} is the largest sector exposure at {pct:.1f}% (hard cap 40%).",
            "metric": f"{pct:.1f}% / 40%",
        })

    # 3. Capital deployment.
    flags.append({
        "id": "deploy",
        "level": "info",
        "title": "Capital deployment",
        "detail": (
            f"Risk engine deployed {gross:.1f}% gross across {summary['numPositions']} "
            f"names, holding {cash:.1f}% in cash."
        ),
        "metric": f"{gross:.1f}% gross",
    })

    # 4. Model conviction / degradation signal.
    if conf["nBuy"]:
        low = conf["meanBuy"] < 50
        flags.append({
            "id": "conviction",
            "level": "warning" if low else "info",
            "title": "Model conviction",
            "detail": (
                f"Mean BUY confidence is {conf['meanBuy']:.1f}% across {conf['nBuy']} BUY signals. "
                + ("Below the 50% conviction guide — size cautiously."
                   if low else "Within the normal research range.")
            ),
            "metric": f"{conf['meanBuy']:.1f}% mean BUY",
        })

    # 5. Provenance / research disclaimer.
    if source == "mock":
        flags.append({
            "id": "source",
            "level": "info",
            "title": "Sample signals",
            "detail": "Risk aggregated on sample signals — run the ML pipeline for live model output.",
            "metric": "sample",
        })
    else:
        flags.append({
            "id": "source",
            "level": "info",
            "title": "Research output",
            "detail": "Exposures derived from experimental model signals. Research use only — not advice.",
            "metric": "experimental",
        })

    return flags


def _volatility_regime() -> list[dict]:
    """Placeholder until price-history-based regime lands (next commit)."""
    import mock_data as mock
    return mock.volatility_regime()


def build_risk_summary() -> dict:
    """Aggregate the live proposed book into the risk summary the UI consumes."""
    signals, source = store.get_signals()
    sector_of = {s["ticker"]: s.get("sector", "—") for s in signals}

    result = propose_orders(signals)
    orders = result["orders"]
    summary = result["summary"]

    cash = _pct(summary["cashWeight"])

    # Exposure by asset — real proposed weights, largest first, + cash.
    asset = sorted(
        ({"name": o.ticker, "value": _pct(o.target_weight)} for o in orders),
        key=lambda x: x["value"],
        reverse=True,
    )[:_TOP_ASSETS]
    if cash > 0:
        asset.append({"name": "Cash", "value": cash})

    # Exposure by sector — from the engine's own sector aggregation, + cash.
    sector = [
        {"name": k, "value": _pct(v)}
        for k, v in sorted(
            summary.get("exposureBySector", {}).items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
    ]
    if cash > 0:
        sector.append({"name": "Cash", "value": cash})

    # Cap-usage budget — every line is a real number vs its hard limit.
    largest_sector = _pct(max(summary.get("exposureBySector", {}).values(), default=0.0))
    budget = [
        {"label": "Gross exposure", "used": _pct(summary["grossExposure"]), "limit": 100},
        {"label": "Single-name max", "used": _pct(summary["largestPosition"]), "limit": 20},
        {"label": "Sector max", "used": largest_sector, "limit": 40},
        {"label": "Active positions", "used": summary["numPositions"], "limit": RiskParams().max_positions},
        {"label": "Cash buffer", "used": cash, "limit": 100},
    ]

    # Concentration metrics (HHI is a real, standard concentration measure).
    weights = [o.target_weight for o in orders]
    hhi = round(sum(w * w for w in weights), 4)
    top3 = _pct(sum(sorted(weights, reverse=True)[:3]))
    conf = _confidence_stats(signals)
    sig_mix = Counter(s.get("signal") for s in signals)

    return {
        "source": source,
        "flags": _flags(signals, summary, orders, source, conf),
        "budget": budget,
        "exposureByAsset": asset,
        "exposureBySector": sector,
        "volatilityRegime": _volatility_regime(),
        "positionRules": POSITION_RULES,
        "concentration": {
            "top1": _pct(summary["largestPosition"]),
            "top3": top3,
            "hhi": hhi,
            "numPositions": summary["numPositions"],
        },
        "confidenceDistribution": conf,
        "signalMix": {"BUY": sig_mix.get("BUY", 0), "HOLD": sig_mix.get("HOLD", 0), "AVOID": sig_mix.get("AVOID", 0)},
    }
