"""Attachment handling: extract text from uploads.

Kinds are detected from filename and mime type:
  * logs / text / json / csv  -> decoded and normalised by log format
  * pdf                       -> extracted with pypdf
  * images                    -> read with the vision model (prompt from prompts.yaml)

Input attachments are ``{"filename", "mime", "bytes"}`` and are returned with
added ``"kind"``, ``"format"``, and ``"text"`` fields.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any

from app.config import settings
from app.llm import get_vision_llm
from app.utils.log_formats import LogFormat, detect_format, normalise_text

logger = logging.getLogger(__name__)

TEXT_EXTS = (
    ".log", ".txt", ".out", ".err", ".trace",
    ".json", ".csv", ".yaml", ".yml",
    ".access", ".error",
)
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
PDF_EXTS = (".pdf",)


def classify(filename: str, mime: str = "") -> str:
    name = (filename or "").lower()
    if name.endswith(TEXT_EXTS) or mime.startswith("text/"):
        return "log"
    if name.endswith(IMAGE_EXTS) or mime.startswith("image/"):
        return "image"
    if name.endswith(PDF_EXTS) or mime == "application/pdf":
        return "pdf"
    return "unknown"


def extract_text(attachment: dict[str, Any]) -> dict[str, Any]:
    """Return the attachment enriched with kind, format, and text."""
    filename = attachment.get("filename", "attachment")
    mime = attachment.get("mime", "")
    raw: bytes = attachment.get("bytes", b"") or b""
    kind = attachment.get("kind") or classify(filename, mime)

    log_format = LogFormat.GENERIC.value
    try:
        if kind == "log":
            decoded = raw.decode("utf-8", errors="replace")
            text, fmt = normalise_text(filename, decoded)
            log_format = fmt.value
        elif kind == "pdf":
            text = _extract_pdf(raw)
        elif kind == "image":
            text = _extract_image(raw, mime, filename)
        else:
            text = ""
    except Exception as exc:
        logger.warning("Failed to extract %s (%s): %s", filename, kind, exc)
        text = ""

    return {
        **attachment,
        "kind": kind,
        "format": log_format,
        "text": text,
    }


def _extract_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed; skipping PDF extraction")
        return ""
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_image(raw: bytes, mime: str, filename: str) -> str:
    """Read text from an image using the vision model and prompts.yaml."""
    if not raw:
        return ""
    prompts = settings.prompt("vision_extraction")
    user_text = prompts.get("user", "Transcribe visible error text from this screenshot.")
    data_url = f"data:{mime or 'image/png'};base64,{base64.b64encode(raw).decode('ascii')}"
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }
    try:
        system = prompts.get("system", "")
        llm = get_vision_llm()
        if system:
            response = llm.invoke([("system", system), message])
        else:
            response = llm.invoke([message])
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("Vision extraction failed for %s: %s", filename, exc)
        return ""
