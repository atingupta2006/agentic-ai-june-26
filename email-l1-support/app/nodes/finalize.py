"""Finalize node.

Promotes the approved draft to the final answer and builds the reference list.
"""
from __future__ import annotations

from app.state import SupportState


def run(state: SupportState) -> dict:
    references: list[str] = []
    seen: set[str] = set()

    def _add(ref: str) -> None:
        if ref and ref not in seen:
            seen.add(ref)
            references.append(ref)

    for m in state.get("kb_matches", []) or []:
        _add(f"KB:{m['id']} (source: {m.get('source')})")
    for m in state.get("web_matches", []) or []:
        _add(m.get("url", ""))

    trace = state.get("trace", []) + ["finalize: answer approved"]
    return {
        "answer": state.get("draft_answer", ""),
        "references": references,
        "status": "answered",
        "trace": trace,
    }
