"""Shared state passed between pipeline nodes.

Each node reads from this dict and returns a partial dict of updates.
"""
from __future__ import annotations

from typing import Any, TypedDict


class SupportState(TypedDict, total=False):
    # Input
    subject: str
    body: str
    attachments: list[dict[str, Any]]

    # Ingest
    log_text: str
    screenshot_findings: str
    attachments_parsed: list[dict[str, Any]]

    # Triage
    category: str
    severity: str
    problem_summary: str
    ticket_status: str

    # Log analysis
    log_findings: dict[str, Any]
    log_excerpts: str
    log_was_large: bool
    log_format: str

    # Retrieval
    kb_matches: list[dict[str, Any]]   # [{id, source, score, text}]
    web_matches: list[dict[str, Any]]  # [{title, url, snippet}]

    # Guardrails
    grounding_score: float
    unsupported_claims: list[str]
    decision: str            # "proceed" | "escalate"
    escalation_reason: str

    # Output
    draft_answer: str
    answer: str
    references: list[str]
    status: str              # "answered" | "escalated"
    trace: list[str]


def new_state(subject: str, body: str, attachments: list[dict[str, Any]] | None = None) -> SupportState:
    return SupportState(
        subject=subject or "",
        body=body or "",
        attachments=attachments or [],
        trace=[],
    )
