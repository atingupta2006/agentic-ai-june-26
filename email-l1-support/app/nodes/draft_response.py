"""Draft response node.

Composes a customer-facing reply from screenshot text, log findings, knowledge
base matches, web references, and ticket status. The draft is audited by the
guardrails node.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.llm import chat
from app.state import SupportState

logger = logging.getLogger(__name__)


def _format_kb(matches: list[dict]) -> str:
    if not matches:
        return "(no internal knowledge base matches found)"
    lines = []
    for m in matches:
        lines.append(f"[KB:{m['id']}] (relevance {m.get('score', 0)})\n{m['text']}")
    return "\n\n".join(lines)


def _format_web(matches: list[dict]) -> str:
    if not matches:
        return "(no web references)"
    lines = []
    for m in matches:
        lines.append(f"[WEB] {m.get('title')} - {m.get('url')}\n{m.get('snippet')}")
    return "\n\n".join(lines)


def _format_findings(findings: dict) -> str:
    if not findings:
        return "(no findings)"
    sigs = ", ".join(findings.get("key_error_signatures", []) or []) or "none"
    return (
        f"Root cause hypothesis: {findings.get('root_cause_hypothesis', 'unknown')}\n"
        f"Key error signatures: {sigs}\n"
        f"Analysis confidence: {findings.get('confidence', 0.0)}"
    )


def run(state: SupportState) -> dict:
    prompts = settings.prompt("draft_response")
    draft = chat(
        prompts["system"],
        prompts["user"].format(
            subject=state.get("subject", ""),
            problem_summary=state.get("problem_summary", ""),
            category=state.get("category", "other"),
            severity=state.get("severity", "medium"),
            ticket_status=state.get("ticket_status") or "(none)",
            screenshot_findings=state.get("screenshot_findings") or "(none)",
            log_findings=_format_findings(state.get("log_findings", {})),
            kb_context=_format_kb(state.get("kb_matches", [])),
            web_context=_format_web(state.get("web_matches", [])),
        ),
    )

    trace = state.get("trace", []) + [f"draft_response: drafted {len(draft)} chars"]
    return {"draft_answer": draft, "trace": trace}
