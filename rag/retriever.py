"""
rag/retriever.py
────────────────
Retrieves relevant document chunks from Mantra's vector database.

Flow:

    User Question
          ↓
    Embedding Model
          ↓
    Query Vector
          ↓
    ChromaDB Search
          ↓
    Relevant Chunks
          ↓
    Context for LLM
"""

from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore

from utils import log


class Retriever:
    """
    Mantra RAG Retriever.

    Converts a user query into an embedding and searches
    the vector database for the most relevant document chunks.
    """

    def __init__(self):

        # Load embedding model
        self.embedding_model = EmbeddingModel()

        # Connect to vector database
        self.vector_store = VectorStore()

        log.info(
            "RAG Retriever initialised successfully."
        )

    # ── Search ─────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        n_results: int = 3
    ) -> list[dict]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query:
                User's question.

            n_results:
                Number of relevant chunks to retrieve.

        Returns:
            List of relevant document chunks.
        """

        if not query or not query.strip():

            log.warning(
                "RAG Retriever received an empty query."
            )

            return []

        log.info(
            f"RAG search query: '{query}'"
        )

        # Convert user question into vector
        query_embedding = (
            self.embedding_model.embed_text(query)
        )

        # Search ChromaDB
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results
        )

        log.info(
            f"RAG found {len(results)} relevant chunks."
        )

        return results

    # ── Build Context ─────────────────────────────────────

    def get_context(
        self,
        query: str,
        n_results: int = 3
    ) -> str:
        """
        Retrieve relevant chunks and combine them into
        one context string for the LLM.

        Args:
            query:
                User's question.

            n_results:
                Number of chunks to include.

        Returns:
            Combined document context.
        """

        results = self.retrieve(
            query=query,
            n_results=n_results
        )

        if not results:

            return ""

        context_parts = []

        for index, result in enumerate(
            results,
            start=1
        ):

            context_parts.append(
                f"[Source {index}: {result['source']} | "
                f"Chunk {result['chunk_number']}]\n"
                f"{result['text']}"
            )

        context = "\n\n---\n\n".join(
            context_parts
        )

        return context

    # ── Database Status ───────────────────────────────────

    def has_documents(self) -> bool:
        """
        Check whether the vector database contains documents.
        """

        return self.vector_store.count() > 0

    def document_count(self) -> int:
        """
        Return total number of chunks stored in the database.
        """

        return self.vector_store.count()


# ── Test ──────────────────────────────────────────────────

if __name__ == "__main__":

    print("Testing Mantra RAG Retriever")
    print("=" * 60)

    retriever = Retriever()

    # Check database
    print(
        f"\nChunks in database: "
        f"{retriever.document_count()}"
    )

    if not retriever.has_documents():

        print(
            "\nNo documents found in vector database."
        )

        print(
            "Run this first:"
        )

        print(
            "python -m rag.ingest"
        )

        raise SystemExit

    # Test questions
    test_questions = [

        "What is CropX?",

        "What technologies are used in the CropX project?",

        "What are the objectives of CropX?"
    ]

    for question in test_questions:

        print("\n" + "=" * 60)

        print(
            f"\nQuestion:\n{question}"
        )

        results = retriever.retrieve(
            question,
            n_results=3
        )

        print(
            "\nTop Relevant Chunks:"
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            print(
                "\n" + "-" * 60
            )

            print(
                f"Result {index}"
            )

            print(
                f"Source: {result['source']}"
            )

            print(
                f"Chunk: {result['chunk_number']}"
            )

            print(
                f"Distance: "
                f"{result['distance']:.4f}"
            )

            print(
                "\nText Preview:"
            )

            print(
                result["text"][:500]
            )

    # ── Context Test ──────────────────────────────────────

    print("\n" + "=" * 60)

    print(
        "\nTesting Context Builder"
    )

    question = (
        "What are the main objectives of CropX?"
    )

    context = retriever.get_context(
        question,
        n_results=3
    )

    print(
        f"\nQuestion:\n{question}"
    )

    print(
        "\nGenerated Context:\n"
    )

    print(context[:2000])

    print("\n" + "=" * 60)

    print(
        "Retriever test completed successfully!"
    )