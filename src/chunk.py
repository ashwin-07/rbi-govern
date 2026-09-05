"""
Three chunking strategies for RBI circular text.

Why three? Each makes a different tradeoff:
  - fixed_size:      simple, predictable size, ignores document structure
  - recursive:       respects paragraph/sentence boundaries, avoids mid-thought cuts
  - clause_hierarchy: domain-specific — RBI circulars use numbered clause trees
                      (1., 1.1, 1.1.1). Keeping clause boundaries intact lets the
                      retriever return self-contained regulatory clauses instead of
                      arbitrary text windows.

The golden-set eval in Week 2 will tell us which strategy wins for this corpus.
"""

import re
from dataclasses import dataclass

_CLAUSE_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]\s+\S", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    chunk_index: int
    strategy: str


# ---------------------------------------------------------------------------
# Strategy 1: Fixed-size (character-based with overlap)
# ---------------------------------------------------------------------------

def fixed_size(text: str, size: int = 1000, overlap: int = 100) -> list[Chunk]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(Chunk(text=chunk, chunk_index=len(chunks), strategy="fixed"))
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Strategy 2: Recursive-semantic (paragraph → sentence → character fallback)
# ---------------------------------------------------------------------------

_SEPARATORS = ["\n\n", "\n", ". ", " "]


def recursive(text: str, max_size: int = 1000) -> list[Chunk]:
    raw = _recursive_split(text.strip(), _SEPARATORS, max_size)
    return [Chunk(text=t, chunk_index=i, strategy="recursive") for i, t in enumerate(raw)]


def _recursive_split(text: str, seps: list[str], max_size: int) -> list[str]:
    if len(text) <= max_size:
        return [text] if text.strip() else []

    sep = seps[0] if seps else None
    if sep is None:
        # Hard character split as last resort
        return [text[:max_size]] + _recursive_split(text[max_size:], [], max_size)

    parts = text.split(sep)
    result: list[str] = []
    current = ""

    for part in parts:
        joined = (current + sep + part).strip() if current else part.strip()
        if len(joined) <= max_size:
            current = joined
        else:
            if current:
                result.append(current)
            if len(part) > max_size:
                result.extend(_recursive_split(part, seps[1:], max_size))
                current = ""
            else:
                current = part.strip()

    if current:
        result.append(current)
    return result


# ---------------------------------------------------------------------------
# Strategy 3: Clause-hierarchy-aware (RBI-specific)
# ---------------------------------------------------------------------------

def clause_hierarchy(text: str, max_size: int = 1000) -> list[Chunk]:
    """
    Split on RBI clause number boundaries: "1.", "1.1", "2.3.4", etc.
    Each chunk is one clause (or a fragment if the clause exceeds max_size).
    The clause number is kept as the first token of its chunk so the retriever
    can always identify which clause it is reading.
    """
    lines = text.split("\n")
    segments: list[str] = []
    current_lines: list[str] = []
    current_clause = ""

    for line in lines:
        m = _CLAUSE_RE.match(line)
        if m:
            if current_lines:
                _flush(current_lines, current_clause, max_size, segments)
            current_lines = [line]
            current_clause = m.group(1)
        else:
            current_lines.append(line)
            # Flush early if current segment is already too large
            accumulated = "\n".join(current_lines)
            if len(accumulated) > max_size:
                _flush(current_lines[:-1], current_clause, max_size, segments)
                current_lines = [f"[{current_clause} cont'd]", line]

    if current_lines:
        _flush(current_lines, current_clause, max_size, segments)

    return [Chunk(text=t, chunk_index=i, strategy="clause") for i, t in enumerate(segments)]


def _flush(lines: list[str], clause: str, max_size: int, out: list[str]) -> None:
    text = "\n".join(lines).strip()
    if not text:
        return
    if len(text) <= max_size:
        out.append(text)
    else:
        # Clause body is still too long — fall back to recursive split
        parts = _recursive_split(text, _SEPARATORS, max_size)
        for i, part in enumerate(parts):
            out.append(part if i == 0 else f"[{clause} cont'd] {part}")
