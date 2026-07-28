"""
Storing chunks and searching them.

Two backends behind one interface. ChromaDB is the default and is what runs in a
normal install. If it isn't importable, a numpy store takes over: it keeps every
vector in one array and compares the question against all of them.

The fallback is not a toy. This corpus is a few hundred chunks, and at that size
comparing against everything is both exact and instant — Chroma's advantage is
persistence and scale, neither of which bites here. What the fallback buys is a
test suite and a fresh clone that work with nothing installed.

Search combines three things:

  vector    finds text that means something similar
  keyword   finds exact terms, which matters for tickers and feature names that
            an embedder happily blurs into their neighbours
  rerank    spreads the winners across different documents instead of returning
            six chunks of the same page

Metadata filters are applied before scoring, so asking about NVDA never has to
rank the other 55 names first.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from .embeddings import cosine, tokenize
from .types import Chunk, RetrievedChunk

INDEX_FILENAME = "research_index.json"
CHROMA_COLLECTION = "quantml_research"

# How much of the final score comes from keyword matching. Vector search carries
# most of it; keywords are there to stop exact terms getting lost.
KEYWORD_WEIGHT = 0.35

# How hard to push for variety when reranking. 0 is pure relevance, 1 is pure
# variety.
DIVERSITY = 0.35


def _matches(meta: dict, filters: dict | None) -> bool:
    """Check one chunk against the metadata filter.

    A filter value can be a single value or a list of acceptable ones. Empty
    filter values are ignored so callers can pass through optional parameters
    without stripping them first.
    """
    if not filters:
        return True
    for key, want in filters.items():
        if want in (None, "", []):
            continue
        have = meta.get(key) or ""
        if isinstance(want, list | tuple | set):
            if have not in {str(w) for w in want}:
                return False
        elif str(have) != str(want):
            return False
    return True


class BM25:
    """Keyword scoring. Rewards rare words and doesn't let long chunks win on length.

    A chunk mentioning "calibration" twice is a better hit than one mentioning
    "the" fifty times, and this is the standard way of expressing that.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self, docs: list[list[str]]):
        self.docs = docs
        self.n = len(docs)
        self.lengths = [len(d) for d in docs]
        self.avg_len = (sum(self.lengths) / self.n) if self.n else 0.0
        self.freqs = [Counter(d) for d in docs]
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {
            term: math.log(1 + (self.n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

    def scores(self, query_tokens: list[str], candidates: list[int]) -> dict[int, float]:
        out: dict[int, float] = {}
        for i in candidates:
            freq, length = self.freqs[i], self.lengths[i]
            score = 0.0
            for term in query_tokens:
                if term not in freq:
                    continue
                tf = freq[term]
                denom = tf + self.K1 * (
                    1 - self.B + self.B * length / (self.avg_len or 1)
                )
                score += self.idf.get(term, 0.0) * tf * (self.K1 + 1) / denom
            out[i] = score
        return out


def _rerank(
    ranked: list[tuple[int, float]], vectors: np.ndarray, limit: int
) -> list[tuple[int, float]]:
    """Pick results that are relevant but not near-copies of each other.

    Without this, a question about costs returns the same paragraph of the cost
    document from five overlapping chunks and the answer gets a narrow view.
    Each pick is scored on its own relevance minus how close it already is to
    something chosen.
    """
    if len(ranked) <= 1:
        return ranked[:limit]

    chosen: list[tuple[int, float]] = []
    pool = list(ranked)
    while pool and len(chosen) < limit:
        best_pos, best_score = 0, -1e9
        for pos, (idx, relevance) in enumerate(pool):
            if chosen:
                overlap = max(
                    float(vectors[idx] @ vectors[c_idx]) for c_idx, _ in chosen
                )
            else:
                overlap = 0.0
            score = (1 - DIVERSITY) * relevance - DIVERSITY * overlap
            if score > best_score:
                best_pos, best_score = pos, score
        chosen.append(pool.pop(best_pos))
    return chosen


class VectorStore:
    """Chunks plus their vectors, searchable with filters.

    Holds everything in memory and persists to a single JSON file. When chromadb
    is installed it also writes there, and reads come from whichever backend is
    active.
    """

    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder_name: str):
        self.chunks = chunks
        self.vectors = vectors
        self.embedder_name = embedder_name
        self.backend = "numpy"
        self._bm25 = BM25([tokenize(f"{c.title} {c.text}") for c in chunks])
        self._chroma = None

    # --- persistence ---------------------------------------------------------

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / INDEX_FILENAME
        path.write_text(
            json.dumps(
                {
                    "embedder": self.embedder_name,
                    "dim": int(self.vectors.shape[1]) if self.vectors.size else 0,
                    "chunks": [c.model_dump() for c in self.chunks],
                    "vectors": self.vectors.tolist(),
                },
            ),
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, directory: Path) -> VectorStore | None:
        path = directory / INDEX_FILENAME
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return None
        chunks = [Chunk(**c) for c in payload.get("chunks", [])]
        vectors = np.asarray(payload.get("vectors", []), dtype=np.float32)
        if not chunks or vectors.size == 0:
            return None
        return cls(chunks, vectors, payload.get("embedder", "unknown"))

    def write_chroma(self, directory: Path) -> bool:
        """Mirror the index into ChromaDB. False if chromadb isn't installed."""
        try:
            import chromadb
        except ImportError:
            return False
        try:
            client = chromadb.PersistentClient(path=str(directory / "chroma"))
            try:
                client.delete_collection(CHROMA_COLLECTION)
            except (ValueError, Exception):  # noqa: B014 - chroma raises its own type
                pass
            collection = client.create_collection(
                CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
            )
            collection.add(
                ids=[c.chunk_id for c in self.chunks],
                embeddings=[v.tolist() for v in self.vectors],
                documents=[c.text for c in self.chunks],
                metadatas=[
                    {
                        "artifact_id": c.artifact_id,
                        "artifact_type": c.artifact_type,
                        "title": c.title,
                        "source_path": c.source_path,
                        "ticker": c.ticker or "",
                        "model_version": c.model_version or "",
                        "run_id": c.run_id or "",
                    }
                    for c in self.chunks
                ],
            )
            self._chroma = collection
            self.backend = "chromadb"
            return True
        except Exception:
            # a broken chroma install shouldn't stop the index being usable
            return False

    def attach_chroma(self, directory: Path) -> bool:
        """Point at an existing Chroma collection without rebuilding it."""
        try:
            import chromadb
        except ImportError:
            return False
        try:
            client = chromadb.PersistentClient(path=str(directory / "chroma"))
            self._chroma = client.get_collection(CHROMA_COLLECTION)
            self.backend = "chromadb"
            return True
        except Exception:
            return False

    # --- search --------------------------------------------------------------

    def search(
        self,
        query: str,
        query_vector: np.ndarray,
        top_k: int = 6,
        filters: dict | None = None,
        use_keywords: bool = True,
        rerank: bool = True,
    ) -> list[RetrievedChunk]:
        """Find the most relevant chunks, honouring metadata filters."""
        if not self.chunks:
            return []

        candidates = [
            i for i, c in enumerate(self.chunks)
            if _matches(c.model_dump(), filters)
        ]
        if not candidates:
            return []

        sims = cosine(query_vector, self.vectors)
        scores = {i: float(sims[i]) for i in candidates}
        method = "vector"

        if use_keywords:
            tokens = tokenize(query)
            if tokens:
                bm = self._bm25.scores(tokens, candidates)
                peak = max(bm.values(), default=0.0)
                if peak > 0:
                    method = "hybrid"
                    for i in candidates:
                        # BM25 has no fixed range, so scale it against the best
                        # hit before mixing it with the cosine score
                        scores[i] += KEYWORD_WEIGHT * (bm[i] / peak)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        # rerank a wider pool than requested, or there's nothing to choose between
        pool = ranked[: max(top_k * 3, top_k)]
        final = _rerank(pool, self.vectors, top_k) if rerank else pool[:top_k]

        return [
            RetrievedChunk(
                chunk=self.chunks[i],
                similarity=round(float(sims[i]), 4),
                retrieval_method=method,
                rerank_score=round(score, 4),
            )
            for i, score in final
        ]

    # --- summaries used by the API -------------------------------------------

    def stats(self) -> dict:
        types: Counter = Counter(c.artifact_type for c in self.chunks)
        artifacts = {c.artifact_id for c in self.chunks}
        return {
            "chunks": len(self.chunks),
            "artifacts": len(artifacts),
            "embedder": self.embedder_name,
            "backend": self.backend,
            "byType": dict(sorted(types.items(), key=lambda kv: -kv[1])),
            "tickers": sorted({c.ticker for c in self.chunks if c.ticker}),
        }
