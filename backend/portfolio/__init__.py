"""
Portfolio / risk layer.

Sits between the signal engine and execution. Takes signals and turns them into
proposed orders under explicit risk limits (sizing, per-name and per-sector caps,
gross cap, regime gate). Pure transform - it proposes orders, it never places them.
"""
from .risk_engine import RiskParams, propose_orders

__all__ = ["RiskParams", "propose_orders"]
