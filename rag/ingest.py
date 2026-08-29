"""
rag/ingest.py
─────────────
Mantra RAG document ingestion pipeline.

Flow:
    rag_documents/
          ↓
    document_loader.py
          ↓
    chunker.py
          ↓
    embeddings.py
          ↓
    vector_store.py
          ↓
    data/vector_db/

Usage:
    python -m rag.ingest
"""

from pathlib import Path

from utils import log
from rag.document_loader import load_folder
from rag.chunker import chunk_documents
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


def ingest_documents(clear_existing: bool = False) -> int:
    """
    Load all documents from rag_documents, split them into
    chunks, create embeddings, and store them in ChromaDB.

    Args:
        clear_existing:
            If True, clears the existing vector database
            before adding documents.

    Returns:
        Total number of chunks stored.
    """

    print("\n" + "=" * 60)
    print("MANTRA RAG - DOCUMENT INGESTION")
    print("=" * 60)

    # ── Project paths ──────────────────────────────────────

    project_root = Path(__file__).resolve().parent.parent

    documents_folder = (
        project_root / "rag_documents"
    )

    print(f"\nDocuments folder:")
    print(documents_folder)

    # ── Check documents folder ─────────────────────────────

    if not documents_folder.exists():

        print(
            "\nERROR: rag_documents folder does not exist."
        )

        log.error(
            f"RAG documents folder not found: "
            f"{documents_folder}"
        )

        return 0

    # ── Step 1: Load documents ─────────────────────────────

    print("\n[1/4] Loading documents...")

    documents = load_folder(
        documents_folder
    )

    if not documents:

        print(
            "No documents found. Nothing to ingest."
        )

        return 0

    print(
        f"Loaded {len(documents)} document(s)."
    )

    # ── Step 2: Create chunks ──────────────────────────────

    print("\n[2/4] Creating chunks...")

    chunks = chunk_documents(
        documents
    )

    if not chunks:

        print(
            "No chunks were created."
        )

        return 0

    print(
        f"Created {len(chunks)} chunks."
    )

    # ── Step 3: Create embeddings ──────────────────────────

    print("\n[3/4] Creating embeddings...")

    embedding_model = EmbeddingModel()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.embed_texts(
        texts
    )

    print(
        f"Created {len(embeddings)} embeddings."
    )

    # ── Step 4: Store in vector database ───────────────────

    print("\n[4/4] Storing in vector database...")

    vector_store = VectorStore()

    if clear_existing:

        print(
            "Clearing existing vector database..."
        )

        vector_store.clear()

    vector_store.add_chunks(
        chunks,
        embeddings
    )

    total_chunks = vector_store.count()

    # ── Completed ──────────────────────────────────────────

    print("\n" + "=" * 60)
    print("INGESTION COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    print(
        f"\nDocuments processed : {len(documents)}"
    )

    print(
        f"Chunks created      : {len(chunks)}"
    )

    print(
        f"Chunks in database  : {total_chunks}"
    )

    print("\nVector database location:")

    print(
        project_root / "data" / "vector_db"
    )

    log.info(
        f"RAG ingestion completed. "
        f"Documents: {len(documents)}, "
        f"Chunks: {len(chunks)}, "
        f"Database total: {total_chunks}"
    )

    return total_chunks


# ── Run directly ──────────────────────────────────────────

if __name__ == "__main__":

    # True means:
    # Clear old data before rebuilding the database.
    ingest_documents(
        clear_existing=True
    )