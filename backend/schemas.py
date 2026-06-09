"""
Pydantic response models for the QuantML API.

These mirror the TypeScript interfaces in `lib/mock-data.ts` exactly, so the
Next.js frontend can switch from its built-in route handlers to this backend by
setting NEXT_PUBLIC_API_URL — no frontend changes required.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

SignalType = Literal["BUY", "HOLD", "AVOID"]
RiskLevel = Literal["Low", "Moderate", "High", "Elevated"]


class Signal(BaseModel):
    ticker: str
    company: str
    signal: SignalType
    confidence: float          # 0-100
    expectedReturn5d: float    # percent
    risk: RiskLevel
    model: str
    drivers: list[str]
    price: float
    change: float
    sector: str


class MetricPoint(BaseModel):
    date: str
    strategy: float
    benchmark: float
    drawdown: float


class Metric(BaseModel):
    key: str
    label: str
    value: float
    suffix: str = ""
    prefix: str = ""
    decimals: int = 0
    delta: float
    spark: int
    up: bool


class ModelRecord(BaseModel):
    id: str
    name: str
    family: str
    status: Literal[
        "Production candidate", "Champion", "Experimental", "Baseline", "Archived"
    ]
    trainingWindow: str
    validation: str
    sharpe: float
    cagr: float
    maxDrawdown: float
    drift: Literal["Low", "Medium", "High"]
    auc: float
    accuracy: float
    features: int
    lastTrained: str
    experimentId: str


class Trade(BaseModel):
    id: str
    date: str
    ticker: str
    side: Literal["LONG", "SHORT"]
    entry: float
    exit: float
    pnl: float
    ret: float
    hold: int


class RiskFlag(BaseModel):
    id: str
    level: Literal["info", "warning", "critical"]
    title: str
    detail: str
    metric: Optional[str] = None


class RagSource(BaseModel):
    title: str
    type: Literal["Filing", "News", "Model report", "Earnings", "Research"]
    date: str
    snippet: str


class SignalContext(BaseModel):
    ticker: str
    signal: SignalType
    confidence: float
    model: str


class RagResponse(BaseModel):
    prompt: str
    answer: str
    sources: list[RagSource]
    signalContext: SignalContext
    riskWarnings: list[str]
    confidence: float


class ResearchRequest(BaseModel):
    prompt: str
