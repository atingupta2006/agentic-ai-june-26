"""Web comparison node.

Searches the web (via SerpAPI) for the error signatures to provide external
references. Skipped if web search is disabled or the API key is missing.
"""
from __future__ import annotations

import logging
import os

from app.config import settings
from app.state import SupportState

logger = logging.getLogger(__name__)


def run(state: SupportState) -> dict:
    if not settings.get("web_search", "enabled", default=False):
        return _skip(state, "disabled in config")

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return _skip(state, "SERPAPI_API_KEY not set")

    findings = state.get("log_findings", {}) or {}
    signatures = findings.get("key_error_signatures", []) or []
    query = signatures[0] if signatures else state.get("problem_summary", "")
    if not query:
        return _skip(state, "no query")

    matches = _serpapi_search(query, api_key)
    trace = state.get("trace", []) + [f"web_compare: query='{query[:50]}', results={len(matches)}"]
    return {"web_matches": matches, "trace": trace}


def _serpapi_search(query: str, api_key: str) -> list[dict]:
    try:
        from serpapi import GoogleSearch
    except ImportError:
        logger.warning("google-search-results not installed; skipping web search")
        return []

    num = settings.get("web_search", "num_results", default=4)
    params = {"engine": "google", "q": query, "api_key": api_key, "num": str(num)}
    try:
        results = GoogleSearch(params).get_dict().get("organic_results", [])
    except Exception as exc:
        logger.warning("SerpAPI search failed: %s", exc)
        return []

    matches = []
    for res in results[:num]:
        matches.append(
            {
                "title": res.get("title", "No title"),
                "url": res.get("link", ""),
                "snippet": res.get("snippet", ""),
            }
        )
    return matches


def _skip(state: SupportState, reason: str) -> dict:
    trace = state.get("trace", []) + [f"web_compare: skipped ({reason})"]
    return {"web_matches": [], "trace": trace}
