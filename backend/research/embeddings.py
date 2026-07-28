"""
Turning text into vectors.

The default is a hashing embedder that needs no model download, no API key and no
network. It scatters each word into a fixed set of buckets and counts what lands
where, which is enough to tell that two pieces of text share vocabulary. That is
a real signal for this corpus, where a question about drawdown genuinely does
share words with the drawdown paragraph.

It is not a semantic model. It cannot tell that "loss" and "drawdown" are related
when the words differ. Swapping in sentence-transformers fixes that and costs a
model download; set RESEARCH_EMBEDDING_PROVIDER=sentence-transformers.

The hashing embedder is deterministic, which is what makes the tests meaningful:
the same text always produces the same vector, on any machine, forever.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

import numpy as np

DIM = 512
TOKEN = re.compile(r"[a-z0-9_]+")

# Words too common to carry meaning. Dropping them stops every chunk looking
# similar to every other chunk just because they all say "the".
STOPWORDS = frozenset("""
a an and are as at be by for from has have how in is it its of on or that the
this to was what when where which who will with why do does did can could
""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def _bucket(token: str) -> int:
    """Map a word to one of DIM buckets. Stable across runs and machines.

    Python's own hash() is deliberately randomised per process, so it can't be
    used here — an index built in one process would be unreadable in the next.
    """
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % DIM


def _sign(token: str) -> float:
    """Half the words count negative, so unrelated words sharing a bucket tend
    to cancel out rather than pile up into a false match."""
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=1).digest()
    return 1.0 if digest[0] % 2 == 0 else -1.0


class HashingEmbedder:
    """Deterministic, offline, no dependencies beyond numpy."""

    name = "hashing-v1"
    dim = DIM

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for i, text in enumerate(texts):
            counts: dict[str, int] = {}
            tokens = tokenize(text)
            for tok in tokens:
                counts[tok] = counts.get(tok, 0) + 1
            # also index adjacent word pairs, so "max drawdown" is distinct from
            # the two words appearing far apart
            for a, b in zip(tokens, tokens[1:], strict=False):
                bigram = f"{a}_{b}"
                counts[bigram] = counts.get(bigram, 0) + 1
            for tok, n in counts.items():
                # log scaling: the tenth mention of a word says much less than the first
                out[i, _bucket(tok)] += _sign(tok) * (1.0 + math.log(n))
            norm = np.linalg.norm(out[i])
            if norm > 0:
                out[i] /= norm
        return out


class SentenceTransformerEmbedder:
    """Real semantic embeddings. Needs the package and a one-off model download."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


@lru_cache(maxsize=4)
def get_embedder(provider: str = "hashing", model_name: str = ""):
    """Build an embedder, falling back to hashing if the real one won't load.

    Falling back rather than raising is deliberate. A missing package should
    degrade the answer quality, not take the endpoint down.
    """
    if provider == "sentence-transformers":
        try:
            return SentenceTransformerEmbedder(
                model_name or "sentence-transformers/all-MiniLM-L6-v2"
            )
        except (ImportError, OSError, ValueError):
            return HashingEmbedder()
    return HashingEmbedder()


def cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Similarity of one vector against many. Both sides are already unit length,
    so the dot product is the cosine."""
    if matrix.size == 0:
        return np.zeros(0, dtype=np.float32)
    return matrix @ query
