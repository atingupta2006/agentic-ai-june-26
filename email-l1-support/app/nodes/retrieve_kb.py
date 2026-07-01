"""Knowledge base retrieval node.

Finds similar past issues in the Chroma knowledge base to use as references.
"""
from __future__ import annotations

import logging

from app.rag.vectorstore import kb_search
from app.state import SupportState

logger = logging.getLogger(__name__)


def run(state: SupportState) -> dict:
    findings = state.get("log_findings", {}) or {}
    signatures = " ".join(findings.get("key_error_signatures", []) or [])
    # Query built from the problem summary and the error signatures.
    query = " ".join(
        part
        for part in [state.get("problem_summary", ""), signatures]
        if part
    ).strip()

    matches = kb_search(query)

    trace = state.get("trace", []) + [
        f"retrieve_kb: query='{query[:60]}...', matches={len(matches)}"
    ]
    return {"kb_matches": matches, "trace": trace}
