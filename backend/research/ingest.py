"""
Building the search index.

    find artifacts -> cut into chunks -> turn into vectors -> save

The built index is cached in memory and on disk. On disk it survives a restart;
in memory it means a question doesn't pay for a rebuild. Anything that changes
the underlying artifacts needs a rebuild, which is what POST /api/research/ingest
is for.
"""
from __future__ import annotations

import time
from pathlib import Path

from config import settings

from . import registry
from .chunking import chunk_all
from .embeddings import get_embedder
from .vectorstore import VectorStore

_cache: VectorStore | None = None


def _index_dir() -> Path:
    return settings.vectorstore_dir


def build_index(persist: bool = True) -> tuple[VectorStore, dict]:
    """Build the index from scratch and return it with a short report."""
    started = time.perf_counter()

    artifacts = registry.discover()
    chunks = chunk_all(artifacts)

    embedder = get_embedder(
        settings.research_embedding_provider, settings.embedding_model
    )
    vectors = (
        embedder.embed([f"{c.title}\n{c.text}" for c in chunks])
        if chunks
        else __import__("numpy").zeros((0, embedder.dim), dtype="float32")
    )

    store = VectorStore(chunks, vectors, embedder.name)

    if persist:
        # The JSON index is always written, so the store still loads whatever
        # the vector backend turns out to be.
        store.save(_index_dir())
        if settings.research_vector_backend != "numpy":
            store.write_chroma(_index_dir())

    global _cache
    _cache = store

    return store, {
        "artifacts": len(artifacts),
        "chunks": len(chunks),
        "embedder": embedder.name,
        "backend": store.backend,
        "elapsedMs": round((time.perf_counter() - started) * 1000, 1),
        "byType": store.stats()["byType"],
    }


def get_index(rebuild: bool = False) -> VectorStore:
    """The current index. Loads from disk, and builds it if there's nothing there."""
    global _cache
    if _cache is not None and not rebuild:
        return _cache
    if not rebuild:
        loaded = VectorStore.load(_index_dir())
        if loaded is not None:
            if settings.research_vector_backend != "numpy":
                loaded.attach_chroma(_index_dir())
            _cache = loaded
            return loaded
    store, _ = build_index()
    return store


def reset_cache() -> None:
    """Drop the in-memory index. Tests use this to force a clean rebuild."""
    global _cache
    _cache = None
