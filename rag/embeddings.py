"""
rag/embeddings.py
─────────────────
Creates semantic embeddings for RAG documents.

Uses SentenceTransformers locally, so after the model is
downloaded once, embeddings can work offline.
"""

from sentence_transformers import SentenceTransformer

from utils import log


# A lightweight and good general-purpose embedding model.
# First run downloads it automatically.
DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingModel:
    """
    Mantra's local text embedding model.

    Converts text into numerical vectors so that semantically
    similar text can be found even when the exact words differ.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name

        log.info(
            f"RAG: Loading embedding model '{model_name}'..."
        )

        self._model = SentenceTransformer(model_name)

        log.info(
            f"RAG: Embedding model loaded successfully: "
            f"'{model_name}'"
        )

    def embed_text(self, text: str) -> list[float]:
        """
        Convert one text string into an embedding vector.

        Returns:
            A list of floating-point numbers.
        """

        if not text or not text.strip():
            return []

        embedding = self._model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 32
    ) -> list[list[float]]:
        """
        Convert multiple texts into embedding vectors.

        Args:
            texts: List of text chunks.
            batch_size: Number of chunks processed together.

        Returns:
            List of embedding vectors.
        """

        if not texts:
            return []

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )

        return embeddings.tolist()


# ── Test ──────────────────────────────────────────────────

if __name__ == "__main__":

    print("Testing Mantra RAG Embeddings")
    print("=" * 60)

    model = EmbeddingModel()

    test_texts = [
        "CropX is an AI-powered crop disease detection system.",
        "The weather in Gujarat is hot today.",
        "Machine learning can identify plant diseases from leaf images."
    ]

    embeddings = model.embed_texts(test_texts)

    print(f"\nModel: {model.model_name}")
    print(f"Texts embedded: {len(embeddings)}")
    print(f"Vector dimensions: {len(embeddings[0])}")

    for i, embedding in enumerate(embeddings):
        print(f"\nText {i + 1}:")
        print(test_texts[i])
        print(
           f"Vector preview: "
            f"{embedding[:10]}"
        )

    print("\n" + "=" * 60)
    print("Embedding test completed successfully!")