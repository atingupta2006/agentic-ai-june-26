"""Build the knowledge base index from source documents.

Reads every ``*.md`` / ``*.txt`` file under ``knowledge_base/``, splits it into
chunks, embeds them, and stores them in Chroma.

    python scripts/build_kb.py
"""
from __future__ import annotations

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.vectorstore import get_kb_store

logger = logging.getLogger(__name__)

KB_EXTS = (".md", ".txt")


def build_knowledge_base() -> int:
    """(Re)build the KB index. Returns the number of chunks indexed."""
    source_dir = settings.resolve_path(
        settings.get("knowledge_base", "source_directory", default="knowledge_base")
    )
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Knowledge base directory not found: {source_dir}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.get("knowledge_base", "chunk_size", default=800),
        chunk_overlap=settings.get("knowledge_base", "chunk_overlap", default=120),
    )

    texts: list[str] = []
    metadatas: list[dict] = []
    files = [p for p in sorted(source_dir.rglob("*")) if p.suffix.lower() in KB_EXTS]
    if not files:
        logger.warning("No KB documents found in %s", source_dir)
        return 0

    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        kb_id = path.stem
        for chunk in splitter.split_text(content):
            texts.append(chunk)
            metadatas.append({"kb_id": kb_id, "source": path.name})

    store = get_kb_store()
    # Reset so re-runs don't create duplicates.
    try:
        store.reset_collection()
    except Exception:
        pass
    store.add_texts(texts=texts, metadatas=metadatas)
    logger.info("Indexed %d chunks from %d KB documents", len(texts), len(files))
    return len(texts)
