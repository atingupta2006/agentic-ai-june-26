"""Escalate node.

Returns an escalation message to the user when guardrails block the draft.
"""
from __future__ import annotations

from app.state import SupportState


def run(state: SupportState) -> dict:
    reason = state.get("escalation_reason") or "insufficient confidence to auto-resolve"
    summary = state.get("problem_summary", "the reported issue")
    severity = state.get("severity", "medium")

    message = (
        "Thank you for contacting support. Your request about "
        f"\"{summary}\" has been escalated to a specialist (severity: {severity}). "
        "A human engineer will follow up shortly."
    )

    trace = state.get("trace", []) + [f"escalate: reason={reason}"]
    return {
        "answer": message,
        "references": [],
        "status": "escalated",
        "trace": trace,
    }
