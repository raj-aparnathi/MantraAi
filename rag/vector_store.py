"""
rag/vector_store.py
───────────────────
Stores and searches Mantra's document chunks using ChromaDB.

Database location:
    data/vector_db/
"""

from pathlib import Path

import chromadb

from utils import log


COLLECTION_NAME = "mantra_documents"


class VectorStore:
    """
    Persistent vector database for Mantra RAG.

    Stores:
        - Chunk text
        - Embedding vector
        - Source filename
        - Original file path
        - Chunk number
    """

    def __init__(self):

        # Find project root
        project_root = Path(__file__).resolve().parent.parent

        # Persistent database location
        db_path = project_root / "data" / "vector_db"

        # Create folder if it doesn't exist
        db_path.mkdir(parents=True, exist_ok=True)

        log.info(
            f"RAG: Opening vector database at: {db_path}"
        )

        # Persistent ChromaDB client
        self._client = chromadb.PersistentClient(
            path=str(db_path)
        )

        # Create collection if it doesn't exist
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "description": "Mantra AI document knowledge base"
            }
        )

        log.info(
            f"RAG: Vector collection ready. "
            f"Documents: {self._collection.count()}"
        )

    # ── Add Chunks ─────────────────────────────────────────

    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]]
    ) -> None:
        """
        Add document chunks and their embeddings to ChromaDB.

        Args:
            chunks:
                List produced by chunk_documents().

            embeddings:
                Corresponding embedding vectors.
        """

        if not chunks:
            log.warning("RAG: No chunks to add.")
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks and embeddings must match."
            )

        ids = []
        documents = []
        metadatas = []

        for index, chunk in enumerate(chunks):

            # Unique ID for every chunk
            chunk_id = (
                f"{chunk['source']}"
                f"_chunk_{chunk['chunk_number']}"
            )

            ids.append(chunk_id)

            documents.append(
                chunk["text"]
            )

            metadatas.append({
                "source": chunk["source"],
                "path": chunk["path"],
                "chunk_number": chunk["chunk_number"],
            })

        # Add to ChromaDB
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        log.info(
            f"RAG: Stored {len(chunks)} chunks successfully."
        )

    # ── Search ─────────────────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5
    ) -> list[dict]:
        """
        Search for document chunks similar to a query.

        Args:
            query_embedding:
                Embedding vector of the user's question.

            n_results:
                Maximum number of relevant chunks to return.

        Returns:
            List of dictionaries containing:
                text
                source
                path
                chunk_number
                distance
        """

        count = self._collection.count()

        if count == 0:
            log.warning(
                "RAG: Vector database is empty."
            )
            return []

        # Never request more results than exist
        n_results = min(n_results, count)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=[
                "documents",
                "metadatas",
                "distances",
            ]
        )

        matches = []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances
        ):

            matches.append({
                "text": document,
                "source": metadata["source"],
                "path": metadata["path"],
                "chunk_number": metadata["chunk_number"],
                "distance": distance,
            })

        return matches

    # ── Database Info ──────────────────────────────────────

    def count(self) -> int:
        """Return the total number of stored chunks."""
        return self._collection.count()

    def clear(self) -> None:
        """
        Delete all stored chunks.

        Useful when you want to rebuild the database.
        """

        self._client.delete_collection(
            COLLECTION_NAME
        )

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME
        )

        log.info("RAG: Vector database cleared.")


# ── Test ──────────────────────────────────────────────────

if __name__ == "__main__":

    from rag.document_loader import load_folder
    from rag.chunker import chunk_documents
    from rag.embeddings import EmbeddingModel

    print("Testing Mantra Vector Store")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    documents_folder = project_root / "rag_documents"

    # Load documents
    documents = load_folder(documents_folder)

    print(f"Documents loaded: {len(documents)}")

    # Create chunks
    chunks = chunk_documents(documents)

    print(f"Chunks created: {len(chunks)}")

    # Load embedding model
    embedding_model = EmbeddingModel()

    # Create vectors
    print("\nCreating embeddings...")

    embeddings = embedding_model.embed_texts(
        [chunk["text"] for chunk in chunks]
    )

    print(
        f"Embeddings created: {len(embeddings)}"
    )

    # Store vectors
    vector_store = VectorStore()

    vector_store.add_chunks(
        chunks,
        embeddings
    )

    print(
        f"\nChunks stored in database: "
        f"{vector_store.count()}"
    )

    # Test semantic search
    test_query = "What is the purpose of the CropX project?"

    print("\n" + "=" * 60)
    print(f"Test Query: {test_query}")

    query_embedding = embedding_model.embed_text(
        test_query
    )

    results = vector_store.search(
        query_embedding,
        n_results=3
    )

    print("\nTop Results:")

    for index, result in enumerate(results, start=1):

        print("\n" + "-" * 60)

        print(f"Result {index}")
        print(f"Source: {result['source']}")
        print(
            f"Chunk: {result['chunk_number']}"
        )
        print(
            f"Distance: {result['distance']:.4f}"
        )

        print("\nText:")
        print(result["text"][:500])

    print("\n" + "=" * 60)
    print("Vector Store test completed successfully!")