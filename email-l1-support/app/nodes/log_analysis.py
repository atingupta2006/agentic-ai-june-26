"""Log analysis node.

Pre-filters log text and includes screenshot text when present. Format-aware
chunking selects the right splitter and embedding model. Large logs are indexed
in memory and the most relevant excerpts are retrieved before the LLM call.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.llm import chat_json
from app.rag.vectorstore import log_index
from app.state import SupportState
from app.utils import log_parser
from app.utils.log_formats import LogFormat, chunk_for_format, detect_format, embedding_profile_for_format

logger = logging.getLogger(__name__)


def _dominant_format(state: SupportState, filtered: str) -> LogFormat:
    metas = state.get("attachments_parsed") or []
    for item in metas:
        if item.get("kind") == "log" and item.get("format"):
            try:
                return LogFormat(item["format"])
            except ValueError:
                pass
    return detect_format("merged.log", filtered)


def run(state: SupportState) -> dict:
    raw = state.get("log_text", "") or ""
    screenshot = (state.get("screenshot_findings") or "").strip()
    if screenshot:
        block = f"===== screenshot =====\n{screenshot}"
        raw = f"{raw}\n\n{block}".strip() if raw.strip() else block

    problem = state.get("problem_summary", "") or state.get("subject", "")

    if not raw.strip():
        trace = state.get("trace", []) + ["log_analysis: no logs or screenshot text"]
        return {
            "log_findings": {"root_cause_hypothesis": "", "key_error_signatures": [], "confidence": 0.0},
            "log_excerpts": "",
            "log_was_large": False,
            "log_format": LogFormat.GENERIC.value,
            "trace": trace,
        }

    filtered = log_parser.prefilter_lines(raw)
    was_large = log_parser.is_large(filtered)
    fmt = _dominant_format(state, filtered)

    if was_large:
        chunks = chunk_for_format(filtered, fmt)
        if not chunks:
            chunks = log_parser.chunk_text(
                filtered,
                chunk_size=settings.get("logs", "chunk_size", default=1200),
                overlap=settings.get("logs", "chunk_overlap", default=150),
            )
        top_k = settings.get("logs", "top_k", default=6)
        query = problem or "error exception failure root cause"
        use_log = embedding_profile_for_format(fmt) == "log"
        try:
            store = log_index(chunks, use_log_embedder=use_log)
            hits = store.similarity_search(query, k=min(top_k, len(chunks)))
            excerpts = "\n\n---\n\n".join(h.page_content for h in hits)
        except Exception as exc:
            logger.warning("Log RAG failed, falling back to head of filtered log: %s", exc)
            excerpts = filtered[: settings.get("logs", "large_log_threshold_chars", default=6000)]
    else:
        excerpts = filtered

    prompts = settings.prompt("log_analysis")
    findings = chat_json(
        prompts["system"],
        prompts["user"].format(problem_summary=problem, log_excerpts=excerpts),
    )
    findings.setdefault("root_cause_hypothesis", "")
    findings.setdefault("key_error_signatures", [])
    findings.setdefault("confidence", 0.0)

    trace = state.get("trace", []) + [
        f"log_analysis: format={fmt.value}, raw={len(raw)} chars, "
        f"filtered={len(filtered)} chars, large={was_large}, excerpts={len(excerpts)} chars"
    ]
    return {
        "log_findings": findings,
        "log_excerpts": excerpts,
        "log_was_large": was_large,
        "log_format": fmt.value,
        "trace": trace,
    }
