"""
Research AI: answering questions about QuantML's own output.

The assistant is deliberately narrow. It reads QuantML artifacts — signals,
feature attribution, validation studies, backtests, the risk framework and the
project documentation — and explains what they say. It has no company
fundamentals, no news and no filings, and it says so rather than filling the gap
from general knowledge.

Search alone would not be enough here. "What is NVDA's confidence" needs the
exact number, and approximately right is wrong. So exact lookups supply the
figures and search supplies the explanation, which is the split the whole package
is built around.
"""
from .service import answer, artifacts, health

__all__ = ["answer", "artifacts", "health"]
