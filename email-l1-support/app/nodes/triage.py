"""Triage node.

Classifies the email (category, severity, summary) and adds ticket status
from the MCP tool.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.llm import chat_json
from app.state import SupportState
from app.tools import mcp_client

logger = logging.getLogger(__name__)


def run(state: SupportState) -> dict:
    prompts = settings.prompt("triage")
    body = state.get("body", "")
    # Include screenshot text in the body for classification.
    if state.get("screenshot_findings"):
        body = f"{body}\n\n[From screenshot]\n{state['screenshot_findings']}"

    parsed = chat_json(
        prompts["system"],
        prompts["user"].format(subject=state.get("subject", ""), body=body),
    )

    category = parsed.get("category", "other")
    severity = parsed.get("severity", "medium")
    summary = parsed.get("summary") or state.get("subject", "")

    # Look up ticket status via the MCP tool.
    ticket_status = mcp_client.call_tool(
        settings.get("mcp", "tool_name", default="lookup_ticket_status"),
        {"subject": state.get("subject", ""), "category": category},
    )

    trace = state.get("trace", []) + [
        f"triage: category={category}, severity={severity}, "
        f"mcp_ticket_status={'ok' if ticket_status else 'n/a'}"
    ]
    return {
        "category": category,
        "severity": severity,
        "problem_summary": summary,
        "ticket_status": ticket_status or "",
        "trace": trace,
    }
