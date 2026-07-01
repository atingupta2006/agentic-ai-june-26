"""Chroma vector store access.

``get_kb_store`` / ``kb_search`` operate on the persistent knowledge base
collection. ``log_index`` builds an in-memory index over a single log file's
chunks for per-request retrieval.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma

from app.config import settings
from app.llm import get_embeddings, get_log_embeddings


@lru_cache(maxsize=1)
def get_kb_store() -> Chroma:
    """Open (or create) the persistent KB collection."""
    persist_dir = settings.resolve_path(
        settings.get("vectorstore", "persist_directory", default="storage/chroma")
    )
    persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.get("vectorstore", "collection_name", default="kb_issues"),
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )


def kb_search(query: str, top_k: int | None = None) -> list[dict]:
    """Similarity search against the persistent KB. Returns normalised dicts."""
    if not query.strip():
        return []
    k = top_k or settings.get("knowledge_base", "top_k", default=4)
    store = get_kb_store()
    try:
        results = store.similarity_search_with_relevance_scores(query, k=k)
    except Exception:
        # Empty or missing collection.
        return []
    matches = []
    for doc, score in results:
        matches.append(
            {
                "id": doc.metadata.get("kb_id", doc.metadata.get("source", "unknown")),
                "source": doc.metadata.get("source", "unknown"),
                "score": round(float(score), 3),
                "text": doc.page_content,
            }
        )
    return matches


def log_index(chunks: list[str], use_log_embedder: bool = True) -> Chroma:
    """Build an in-memory index over log chunks (not persisted to disk)."""
    embedder = get_log_embeddings() if use_log_embedder else get_embeddings()
    store = Chroma(
        collection_name="ephemeral_logs",
        embedding_function=embedder,
    )
    metadatas = [{"chunk": i} for i in range(len(chunks))]
    store.add_texts(texts=chunks, metadatas=metadatas)
    return store
