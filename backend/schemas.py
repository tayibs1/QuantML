"""
Pydantic response models for the QuantML API.

These mirror the TypeScript interfaces in `lib/mock-data.ts` exactly, so the
Next.js frontend can switch from its built-in route handlers to this backend by
setting NEXT_PUBLIC_API_URL — no frontend changes required.
"""
from __future__ import annotations

from typing import Literal

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
    metric: str | None = None


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


# --- Research AI (retrieval-grounded answers over QuantML artifacts) ---

class ResearchQuery(BaseModel):
    """A question for the research assistant, plus optional narrowing."""
    question: str
    ticker: str | None = None
    model_version: str | None = None
    run_id: str | None = None
    top_k: int | None = None


class ResearchSource(BaseModel):
    """One cited piece of evidence, either an exact lookup or a retrieved chunk."""
    tag: str                       # the [S1]/[E2] marker used in the answer
    kind: Literal["structured", "retrieved"]
    artifact_id: str
    artifact_type: str
    title: str
    source_path: str
    heading: str | None = None
    chunk_id: str | None = None
    similarity: float | None = None
    snippet: str | None = None


class ResearchEvidence(BaseModel):
    """A retrieved passage, shown in full in the evidence panel."""
    chunk_id: str
    artifact_id: str
    artifact_type: str
    title: str
    heading: str | None = None
    source_path: str
    similarity: float
    retrieval_method: str
    text: str


class ResearchAnswer(BaseModel):
    question: str
    answer: str
    intent: str
    ticker: str | None = None
    signal_context: dict | None = None
    sources: list[ResearchSource]
    evidence: list[ResearchEvidence]
    tool_calls: list[dict]
    retrieval_trace: list[dict]
    # non-empty means something about the answer needs a second look
    grounding_warnings: list[str]
    grounded: bool
    llm: dict
    latency_ms: float
    over_latency_budget: bool


class BacktestRequest(BaseModel):
    """Caller-tunable backtest settings (camelCase to match the frontend form)."""
    rebalance: Literal["Daily", "Weekly", "Monthly"] = "Weekly"
    topN: int = 20
    commissionBps: float = 5.0
    slippageBps: float = 8.0
    model: str = "XGBoost-v3"

    def to_engine_config(self) -> dict:
        return {
            "rebalance": self.rebalance,
            "top_n": self.topN,
            "commission_bps": self.commissionBps,
            "slippage_bps": self.slippageBps,
            "model": self.model,
        }
