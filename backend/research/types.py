"""
The shapes the research assistant passes around.

Two things travel through the system. An Artifact is one piece of QuantML
evidence: a signal, a backtest report, a page of documentation. A Chunk is a
slice of one small enough to hand to a language model, and it keeps a pointer
back to where it came from so every claim can be traced to a source.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Grouping artifacts by type is what lets a question about validation search only
# validation material instead of the whole corpus.
ArtifactType = Literal[
    "latest_signal",
    "signal_history",
    "shap_summary",
    "feature_dictionary",
    "validation_report",
    "walk_forward_report",
    "backtest_report",
    "risk_report",
    "model_card",
    "model_registry_entry",
    "drift_report",
    "calibration_report",
    "documentation",
    "research_note",
]


class Artifact(BaseModel):
    """One piece of QuantML evidence, with enough metadata to filter and cite it."""

    artifact_id: str
    artifact_type: ArtifactType
    title: str
    text: str
    source_path: str
    ticker: str | None = None
    model_version: str | None = None
    run_id: str | None = None
    date_range: str | None = None
    created_at: str | None = None
    # Exact figures pulled out of the artifact. The structured tools read these
    # so numbers never have to be parsed back out of prose.
    numeric: dict[str, float] = Field(default_factory=dict)

    def metadata(self) -> dict:
        """The filterable fields, flattened for the vector store."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "source_path": self.source_path,
            "ticker": self.ticker or "",
            "model_version": self.model_version or "",
            "run_id": self.run_id or "",
            "date_range": self.date_range or "",
            "created_at": self.created_at or "",
        }


class Chunk(BaseModel):
    """A slice of an artifact, sized to fit in a prompt."""

    chunk_id: str
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    text: str
    source_path: str
    ticker: str | None = None
    model_version: str | None = None
    run_id: str | None = None
    date_range: str | None = None
    created_at: str | None = None
    heading: str | None = None
    position: int = 0


class RetrievedChunk(BaseModel):
    """A chunk that came back from a search, with how it scored and why."""

    chunk: Chunk
    similarity: float
    # "vector", "keyword" or "hybrid" - useful when checking why something ranked
    retrieval_method: str = "vector"
    rerank_score: float | None = None


class ToolCall(BaseModel):
    """A record of one exact-lookup call, kept so the answer can be audited."""

    tool: str
    arguments: dict
    ok: bool
    result: dict | list | None = None
    note: str | None = None


class RetrievalStep(BaseModel):
    """One line of the trace explaining how evidence was gathered."""

    step: str
    detail: str
    result_count: int = 0
