"""LLM and embeddings factory.

Creates the models named in app.yaml, cached so they are instantiated once.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.get("llm", "model", default="gpt-4o-mini"),
        temperature=settings.get("llm", "temperature", default=0.0),
        timeout=settings.get("llm", "request_timeout_seconds", default=60),
    )


@lru_cache(maxsize=1)
def get_vision_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.get("llm", "vision_model", default="gpt-4o-mini"),
        temperature=0.0,
        timeout=settings.get("llm", "request_timeout_seconds", default=60),
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.get("embeddings", "model", default="text-embedding-3-small"),
    )


@lru_cache(maxsize=1)
def get_log_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.get("embeddings", "log_model", default="text-embedding-3-large"),
    )


def chat(system: str, user: str) -> str:
    """Single chat call returning plain text."""
    llm = get_llm()
    response = llm.invoke([("system", system), ("human", user)])
    return response.content if hasattr(response, "content") else str(response)


def chat_json(system: str, user: str) -> dict[str, Any]:
    """Chat helper that parses the reply into a JSON dict.

    Extracts the first JSON object from the reply, returning an empty dict on
    failure so callers can fall back to defaults.
    """
    raw = chat(system, user)
    return _extract_json(raw)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip code fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
