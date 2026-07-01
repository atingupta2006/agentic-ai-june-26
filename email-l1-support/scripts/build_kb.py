"""Build / rebuild the knowledge base vector index.

Usage:
    python scripts/build_kb.py
"""
import _bootstrap  # noqa: F401  (adds project root to sys.path)

from app.rag.ingest_kb import build_knowledge_base


def main() -> None:
    print("Indexing knowledge base into Chroma...")
    count = build_knowledge_base()
    print(f"Done. Indexed {count} chunks.")


if __name__ == "__main__":
    main()
