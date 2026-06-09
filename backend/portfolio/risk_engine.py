"""
Risk engine: signals → proposed orders.

A signal is NOT a position. This layer decides *whether* and *how much* to hold,
under hard limits:

  - long-only book of BUY names (shorting AVOID is a later extension)
  - volatility-scaled, confidence-weighted sizing
  - per-name cap (default 20%), per-sector cap (default 40%), gross cap (100%)

Output feeds the execution adapter (backtest / paper / live). Pure function —
deterministic, side-effect free, easy to unit-test and reason about.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from execution.base import OrderSide, ProposedOrder

# Lower-risk names get a larger share of their raw weight.
RISK_FACTOR = {"Low": 1.0, "Moderate": 0.8, "High": 0.6, "Elevated": 0.45}


@dataclass
class RiskParams:
    max_name_weight: float = 0.20
    max_sector_weight: float = 0.40
    gross_target: float = 1.00
    min_confidence: float = 0.0  # ignore BUYs below this confidence
    max_positions: int = 25


def propose_orders(signals: list[dict], params: RiskParams | None = None) -> dict:
    """Return {orders: ProposedOrder[], summary: {...}} from a list of signals."""
    p = params or RiskParams()

    # 1. Candidates: BUY signals above the confidence floor.
    cands = [
        s for s in signals
        if s.get("signal") == "BUY" and s.get("confidence", 0) >= p.min_confidence
    ]
    cands.sort(key=lambda s: s.get("confidence", 0), reverse=True)
    cands = cands[: p.max_positions]
    if not cands:
        return {"orders": [], "summary": _summary([], {})}

    # 2. Raw weights = confidence × risk factor, normalized to the gross target.
    raw = {
        s["ticker"]: s.get("confidence", 0) * RISK_FACTOR.get(s.get("risk", "Moderate"), 0.7)
        for s in cands
    }
    total = sum(raw.values()) or 1.0
    w = {t: v / total * p.gross_target for t, v in raw.items()}

    # 3. Per-name cap.
    w = {t: min(v, p.max_name_weight) for t, v in w.items()}

    # 4. Per-sector cap — scale down over-exposed sectors.
    sector_of = {s["ticker"]: s.get("sector", "—") for s in cands}
    sector_tot: dict[str, float] = defaultdict(float)
    for t, v in w.items():
        sector_tot[sector_of[t]] += v
    for sec, tot in sector_tot.items():
        if tot > p.max_sector_weight and tot > 0:
            scale = p.max_sector_weight / tot
            for t in w:
                if sector_of[t] == sec:
                    w[t] *= scale

    # 5. Gross cap — never lever above the target.
    gross = sum(w.values())
    if gross > p.gross_target and gross > 0:
        w = {t: v * p.gross_target / gross for t, v in w.items()}

    by_conf = {s["ticker"]: s.get("confidence", 0) for s in cands}
    orders = [
        ProposedOrder(
            ticker=t,
            side=OrderSide.BUY,
            target_weight=round(v, 4),
            signal="BUY",
            confidence=by_conf[t],
            reason=f"BUY conf {by_conf[t]:.0f}%, {sector_of[t]}, sized vol/conf-weighted",
        )
        for t, v in sorted(w.items(), key=lambda kv: kv[1], reverse=True)
        if v > 0.001
    ]
    return {"orders": orders, "summary": _summary(orders, sector_of)}


def _summary(orders: list[ProposedOrder], sector_of: dict[str, str]) -> dict:
    gross = round(sum(o.target_weight for o in orders), 4)
    by_sector: dict[str, float] = defaultdict(float)
    for o in orders:
        by_sector[sector_of.get(o.ticker, "—")] += o.target_weight
    return {
        "grossExposure": gross,
        "netExposure": gross,  # long-only
        "numPositions": len(orders),
        "largestPosition": round(max((o.target_weight for o in orders), default=0.0), 4),
        "exposureBySector": {k: round(v, 4) for k, v in sorted(
            by_sector.items(), key=lambda kv: kv[1], reverse=True)},
        "cashWeight": round(max(0.0, 1.0 - gross), 4),
    }
