"""Guardrails node — uses the guardrails-ai library.

Policy keywords, reference count, and grounding audit are implemented as
custom validators in ``app.guardrails_engine``. Prompt text for grounding
still comes from ``config/prompts.yaml``.

``route`` returns the decision for the conditional edge in graph.yaml.
"""
from __future__ import annotations

import logging

from app.guardrails_engine import validate_draft
from app.state import SupportState

logger = logging.getLogger(__name__)


def _build_evidence(state: SupportState) -> str:
    parts: list[str] = []
    findings = state.get("log_findings", {}) or {}
    if findings.get("root_cause_hypothesis"):
        parts.append("LOG FINDINGS: " + findings["root_cause_hypothesis"])
    if state.get("screenshot_findings"):
        parts.append("SCREENSHOT: " + state["screenshot_findings"])
    if state.get("ticket_status"):
        parts.append("TICKET STATUS: " + state["ticket_status"])
    for m in state.get("kb_matches", []) or []:
        parts.append(f"KB:{m['id']}: {m['text']}")
    for m in state.get("web_matches", []) or []:
        parts.append(f"WEB:{m.get('url')}: {m.get('snippet')}")
    return "\n\n".join(parts) if parts else "(no evidence)"


def run(state: SupportState) -> dict:
    draft = state.get("draft_answer", "") or ""
    ticket_text = " ".join(
        [state.get("subject", ""), state.get("body", ""), state.get("problem_summary", "")]
    )
    evidence = _build_evidence(state)
    num_refs = len(state.get("kb_matches", []) or []) + len(state.get("web_matches", []) or [])

    outcome = validate_draft(
        draft,
        ticket_text=ticket_text,
        evidence=evidence,
        num_refs=num_refs,
    )

    trace = state.get("trace", []) + [
        f"guardrails: decision={outcome.decision}, grounding={outcome.grounding_score:.2f}, "
        f"refs={num_refs}, reasons={outcome.escalation_reason or 'none'}"
    ]
    updates: dict = {
        "grounding_score": outcome.grounding_score,
        "unsupported_claims": outcome.unsupported_claims,
        "decision": outcome.decision,
        "escalation_reason": outcome.escalation_reason,
        "trace": trace,
    }
    if outcome.validated_draft and outcome.validated_draft != draft:
        updates["draft_answer"] = outcome.validated_draft
    return updates


def route(state: SupportState) -> str:
    return state.get("decision", "escalate")
