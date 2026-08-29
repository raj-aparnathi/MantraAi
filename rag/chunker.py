"""
rag/chunker.py
──────────────
Splits large documents into small overlapping chunks
for RAG retrieval.

Each chunk keeps metadata about its original document.
"""

from typing import Any


# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks.

    The function tries to split at natural boundaries such as:
        1. Paragraphs
        2. Sentences
        3. Spaces

    Args:
        text: Full document text.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters shared between chunks.

    Returns:
        List of text chunks.
    """

    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    text = text.strip()
    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        # If this is not the last chunk,
        # try to find a natural place to split.
        if end < text_length:

            search_area = text[start:end]

            # Priority 1: paragraph break
            split_point = search_area.rfind("\n\n")

            # Priority 2: newline
            if split_point == -1:
                split_point = search_area.rfind("\n")

            # Priority 3: sentence ending
            if split_point == -1:
                for separator in [". ", "! ", "? "]:
                    split_point = search_area.rfind(separator)

                    if split_point != -1:
                        split_point += len(separator)
                        break

            # Priority 4: nearest space
            if split_point == -1:
                split_point = search_area.rfind(" ")

            # Only use natural split if it isn't
            # too close to the beginning.
            if split_point > chunk_size * 0.5:
                end = start + split_point

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # Reached the end
        if end >= text_length:
            break

        # Move forward while keeping overlap
        start = max(
            end - overlap,
            start + 1
        )

    return chunks


def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """
    Convert loaded documents into RAG-ready chunks.

    Input example:
        {
            "path": "...",
            "filename": "CropX_Project.pdf",
            "text": "Full document text..."
        }

    Output example:
        {
            "text": "Chunk text...",
            "source": "CropX_Project.pdf",
            "path": "D:/.../CropX_Project.pdf",
            "chunk_number": 0
        }
    """

    all_chunks = []

    for document in documents:

        text_chunks = chunk_text(
            text=document["text"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_number, chunk in enumerate(text_chunks):

            all_chunks.append({
                "text": chunk,
                "source": document["filename"],
                "path": document["path"],
                "chunk_number": chunk_number,
            })

    return all_chunks


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    from pathlib import Path
    from rag.document_loader import load_folder

    print("Testing RAG Chunker")
    print("=" * 60)

    # Project root
    project_root = Path(__file__).resolve().parent.parent

    # Load documents
    documents_folder = project_root / "rag_documents"

    documents = load_folder(documents_folder)

    print(f"Documents loaded: {len(documents)}")

    # Convert documents into chunks
    chunks = chunk_documents(documents)

    print(f"Total chunks created: {len(chunks)}")

    # Show first 3 chunks
    for chunk in chunks[:3]:

        print("\n" + "=" * 60)

        print(f"Source       : {chunk['source']}")
        print(f"Chunk Number : {chunk['chunk_number']}")
        print(f"Path         : {chunk['path']}")
        print(f"Characters   : {len(chunk['text'])}")

        print("\nText Preview:")
        print(chunk["text"][:500])

    print("\n" + "=" * 60)
    print("Chunker test completed!")