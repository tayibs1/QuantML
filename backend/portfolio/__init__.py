"""
Portfolio / Risk layer.

The bridge between the signal engine and execution: it turns *signals* into
*proposed orders* under explicit risk limits (sizing, per-name / per-sector caps,
gross cap, regime gate). It is a pure transform — it proposes, it never executes.
"""
from .risk_engine import RiskParams, propose_orders

__all__ = ["RiskParams", "propose_orders"]
