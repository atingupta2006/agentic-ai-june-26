"""Log pre-processing utilities.

``prefilter_lines`` keeps only lines matching the configured patterns, and
``chunk_text`` splits text for retrieval. Both are deterministic and make no
LLM calls.
"""
from __future__ import annotations

import re

from app.config import settings


def _compiled_patterns() -> list[re.Pattern]:
    patterns = settings.get("logs", "interesting_patterns", default=[])
    return [re.compile(p) for p in patterns]


def prefilter_lines(log_text: str, context_lines: int = 1) -> str:
    """Keep only lines matching the 'interesting' patterns, plus a little
    surrounding context so stack traces stay readable.
    """
    if not log_text:
        return ""

    patterns = _compiled_patterns()
    if not patterns:
        return log_text

    lines = log_text.splitlines()
    keep: set[int] = set()
    for i, line in enumerate(lines):
        if any(p.search(line) for p in patterns):
            lo = max(0, i - context_lines)
            hi = min(len(lines), i + context_lines + 1)
            keep.update(range(lo, hi))

    if not keep:
        # Nothing matched; return a small head sample.
        return "\n".join(lines[:50])

    ordered = sorted(keep)
    out: list[str] = []
    prev = None
    for idx in ordered:
        if prev is not None and idx != prev + 1:
            out.append("...")  # marks a gap between non-contiguous regions
        out.append(lines[idx])
        prev = idx
    return "\n".join(out)


def is_large(text: str) -> bool:
    threshold = settings.get("logs", "large_log_threshold_chars", default=6000)
    return len(text) > int(threshold)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character-based chunking with overlap."""
    if chunk_size <= 0:
        return [text]
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap if end - overlap > start else end
    return chunks
