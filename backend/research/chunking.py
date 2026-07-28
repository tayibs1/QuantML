"""
Cut artifacts into pieces small enough to put in a prompt.

Long documents are split on their markdown headings, because a heading marks a
change of subject and splitting there keeps each piece about one thing. Short
artifacts, which is most of the generated ones, stay whole.

Chunk ids are built from the artifact id and the position, so the same input
always produces the same ids. That matters: citations in a stored answer stay
valid after the index is rebuilt.
"""
from __future__ import annotations

import re

from .types import Artifact, Chunk

# Roughly a paragraph or two. Big enough to carry an argument, small enough that
# six of them still leave room for the question and the answer.
MAX_CHARS = 1400
OVERLAP_CHARS = 150
MIN_CHARS = 40

HEADING = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)


def _split_on_headings(text: str) -> list[tuple[str | None, str]]:
    """Break markdown into (heading, body) sections. No headings means one section."""
    matches = list(HEADING.finditer(text))
    if not matches:
        return [(None, text)]

    sections = []
    preamble = text[: matches[0].start()].strip()
    if len(preamble) >= MIN_CHARS:
        sections.append((None, preamble))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            sections.append((m.group(2).strip(), body))
    return sections


def _split_long(text: str) -> list[str]:
    """Break an over-long section on blank lines, carrying a little overlap.

    The overlap means a sentence that straddles a boundary still appears whole
    in one of the pieces.
    """
    if len(text) <= MAX_CHARS:
        return [text]

    parts: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        if buf and len(buf) + len(para) + 2 > MAX_CHARS:
            parts.append(buf.strip())
            buf = buf[-OVERLAP_CHARS:] + "\n\n" + para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf.strip():
        parts.append(buf.strip())

    # a single paragraph longer than the limit still has to be cut somewhere
    out: list[str] = []
    for p in parts:
        while len(p) > MAX_CHARS * 1.5:
            out.append(p[:MAX_CHARS])
            p = p[MAX_CHARS - OVERLAP_CHARS:]
        out.append(p)
    return out


def chunk_artifact(artifact: Artifact) -> list[Chunk]:
    """Split one artifact into chunks, keeping its metadata on every piece."""
    chunks: list[Chunk] = []
    position = 0

    for heading, body in _split_on_headings(artifact.text):
        for piece in _split_long(body):
            piece = piece.strip()
            if len(piece) < MIN_CHARS:
                continue
            # prepend the heading so a chunk read on its own still has context
            text = f"{heading}\n\n{piece}" if heading else piece
            chunks.append(
                Chunk(
                    chunk_id=f"{artifact.artifact_id}#{position}",
                    artifact_id=artifact.artifact_id,
                    artifact_type=artifact.artifact_type,
                    title=artifact.title,
                    text=text,
                    source_path=artifact.source_path,
                    ticker=artifact.ticker,
                    model_version=artifact.model_version,
                    run_id=artifact.run_id,
                    date_range=artifact.date_range,
                    created_at=artifact.created_at,
                    heading=heading,
                    position=position,
                )
            )
            position += 1

    # an artifact too short to survive the minimum still deserves one chunk
    if not chunks and artifact.text.strip():
        chunks.append(
            Chunk(
                chunk_id=f"{artifact.artifact_id}#0",
                artifact_id=artifact.artifact_id,
                artifact_type=artifact.artifact_type,
                title=artifact.title,
                text=artifact.text.strip(),
                source_path=artifact.source_path,
                ticker=artifact.ticker,
                model_version=artifact.model_version,
                run_id=artifact.run_id,
                date_range=artifact.date_range,
                created_at=artifact.created_at,
            )
        )
    return chunks


def chunk_all(artifacts: list[Artifact]) -> list[Chunk]:
    out: list[Chunk] = []
    for a in artifacts:
        out.extend(chunk_artifact(a))
    return out
