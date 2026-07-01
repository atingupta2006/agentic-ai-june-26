"""Detect and normalise common log and export formats.

Each format maps to a chunking strategy and an embedding profile (see
``config/app.yaml`` -> ``embeddings`` and ``logs.formats``).
"""
from __future__ import annotations

import csv
import io
import json
import re
from enum import Enum

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


class LogFormat(str, Enum):
    GENERIC = "generic"
    JAVA_SPRING = "java_spring"
    APACHE_ACCESS = "apache_access"
    APACHE_ERROR = "apache_error"
    NGINX_ACCESS = "nginx_access"
    NGINX_ERROR = "nginx_error"
    JSON_LINES = "json_lines"
    JSON_ARRAY = "json_array"
    CSV = "csv"


_APACHE_ACCESS = re.compile(r'^\S+ \S+ \S+ \[.+\] ".+" \d{3}')
_APACHE_ERROR = re.compile(r"^\[(?:\w+ \w+|\w+):(?:error|emerg|alert|crit|warn)\]", re.I)
_NGINX_ERROR = re.compile(
    r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} \[(error|warn|crit|alert|emerg)\]", re.I
)
_JAVA_TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+(INFO|WARN|ERROR|DEBUG|TRACE)")


def detect_format(filename: str, text: str) -> LogFormat:
    """Guess the format from the filename and the first non-empty lines."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return LogFormat.CSV
    if name.endswith(".json"):
        stripped = text.lstrip()
        if stripped.startswith("["):
            return LogFormat.JSON_ARRAY
        return LogFormat.JSON_LINES

    lines = [ln for ln in text.splitlines() if ln.strip()][:30]
    if not lines:
        return LogFormat.GENERIC

    apache_err = sum(1 for ln in lines if _APACHE_ERROR.search(ln))
    nginx_err = sum(1 for ln in lines if _NGINX_ERROR.search(ln))
    apache_acc = sum(1 for ln in lines if _APACHE_ACCESS.search(ln))
    java = sum(1 for ln in lines if _JAVA_TS.search(ln))

    if apache_err >= 2:
        return LogFormat.APACHE_ERROR
    if nginx_err >= 2:
        return LogFormat.NGINX_ERROR
    if apache_acc >= 3:
        return LogFormat.APACHE_ACCESS
    if java >= 3:
        return LogFormat.JAVA_SPRING
    if "nginx" in name and "access" in name:
        return LogFormat.NGINX_ACCESS
    if "nginx" in name and "error" in name:
        return LogFormat.NGINX_ERROR
    if "apache" in name or "access.log" in name:
        return LogFormat.APACHE_ACCESS
    return LogFormat.GENERIC


def normalise_text(filename: str, raw_text: str) -> tuple[str, LogFormat]:
    """Return searchable plain text and the detected format."""
    fmt = detect_format(filename, raw_text)
    if fmt == LogFormat.CSV:
        return _normalise_csv(raw_text), fmt
    if fmt == LogFormat.JSON_ARRAY:
        return _normalise_json_array(raw_text), fmt
    if fmt == LogFormat.JSON_LINES:
        return _normalise_json_lines(raw_text), fmt
    return raw_text, fmt


def _normalise_csv(text: str) -> str:
    reader = csv.DictReader(io.StringIO(text))
    lines: list[str] = []
    for row in reader:
        level = (row.get("level") or row.get("severity") or row.get("status") or "").upper()
        msg = row.get("message") or row.get("msg") or row.get("error") or json.dumps(row)
        ts = row.get("timestamp") or row.get("ts") or row.get("time") or ""
        lines.append(f"{ts} {level} {msg}".strip())
    return "\n".join(lines) if lines else text


def _normalise_json_array(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(data, list):
        return text
    lines: list[str] = []
    for item in data:
        if isinstance(item, dict):
            level = item.get("level", "INFO")
            logger = item.get("logger", item.get("service", ""))
            msg = item.get("msg", item.get("message", item))
            ts = item.get("ts", item.get("timestamp", ""))
            lines.append(f"{ts} {level} {logger}: {msg}")
        else:
            lines.append(str(item))
    return "\n".join(lines)


def _normalise_json_lines(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            lines.append(raw)
            continue
        if isinstance(obj, dict):
            level = obj.get("level", "INFO")
            logger = obj.get("logger", obj.get("service", ""))
            msg = obj.get("msg", obj.get("message", obj))
            ts = obj.get("ts", obj.get("timestamp", ""))
            lines.append(f"{ts} {level} {logger}: {msg}")
        else:
            lines.append(str(obj))
    return "\n".join(lines)


def _format_cfg(fmt: LogFormat) -> dict:
    formats = settings.get("logs", "formats", default={}) or {}
    return formats.get(fmt.value, formats.get("generic", {}))


def chunk_for_format(text: str, fmt: LogFormat) -> list[str]:
    """Pick a chunker based on the detected log format."""
    cfg = _format_cfg(fmt)
    strategy = cfg.get("chunker", "recursive")

    if strategy == "line":
        lines_per = int(cfg.get("lines_per_chunk", 40))
        overlap_lines = int(cfg.get("line_overlap", 5))
        lines = text.splitlines()
        if not lines:
            return []
        chunks: list[str] = []
        step = max(1, lines_per - overlap_lines)
        for start in range(0, len(lines), step):
            block = lines[start : start + lines_per]
            if block:
                chunks.append("\n".join(block))
        return chunks

    size = int(cfg.get("chunk_size", settings.get("logs", "chunk_size", default=1200)))
    overlap = int(cfg.get("chunk_overlap", settings.get("logs", "chunk_overlap", default=150)))
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_text(text)


def embedding_profile_for_format(fmt: LogFormat) -> str:
    """Return ``kb`` or ``log`` — selects which embedding model to use."""
    cfg = _format_cfg(fmt)
    return cfg.get("embedding_profile", "log")
