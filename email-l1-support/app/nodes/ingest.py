"""Ingest node.

Extracts text from attachments: log/text/pdf content is collected into
``log_text``, and image attachments are read by the vision model into
``screenshot_findings``. Each attachment's detected log format is recorded.
"""
from __future__ import annotations

import logging

from app.state import SupportState
from app.utils.attachments import extract_text

logger = logging.getLogger(__name__)


def run(state: SupportState) -> dict:
    attachments = state.get("attachments", []) or []
    log_parts: list[str] = []
    screenshot_parts: list[str] = []
    parsed_meta: list[dict] = []

    for att in attachments:
        enriched = extract_text(att)
        text = (enriched.get("text") or "").strip()
        parsed_meta.append({
            "filename": enriched.get("filename", ""),
            "kind": enriched.get("kind", ""),
            "format": enriched.get("format", "generic"),
            "chars": len(text),
        })
        if not text:
            continue
        if enriched["kind"] == "image":
            screenshot_parts.append(f"[{enriched.get('filename', 'image')}]\n{text}")
        else:
            header = enriched.get("filename", "attachment")
            fmt = enriched.get("format", "generic")
            log_parts.append(f"===== {header} ({fmt}) =====\n{text}")

    log_text = "\n\n".join(log_parts)
    screenshot_findings = "\n\n".join(screenshot_parts)

    trace = state.get("trace", []) + [
        f"ingest: {len(attachments)} attachment(s); "
        f"{len(log_text)} log chars; {len(screenshot_parts)} screenshot(s)"
    ]
    return {
        "log_text": log_text,
        "screenshot_findings": screenshot_findings,
        "attachments_parsed": parsed_meta,
        "trace": trace,
    }
