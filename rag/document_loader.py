"""
rag/document_loader.py
──────────────────────
Loads and cleans text from supported document types.

Supported:
    - PDF
    - DOCX
    - TXT
"""

from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader
from docx import Document


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def clean_text(text: str) -> str:
    """
    Clean extracted document text and fix common PDF
    Unicode / ligature extraction problems.
    """

    if not text:
        return ""

    # Normalize common Unicode characters first
    text = unicodedata.normalize("NFKC", text)

    # Some PDFs contain special characters that don't normalize correctly
    replacements = {
        "Ɵ": "ti",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ﬆ": "st",
        "ƞ": "tf",
        "Ō": "ft",
        "ō": "ft",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Fix line-break hyphenation:
    # Example: "artifi-\ncial" → "artificial"
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # Clean spaces on each line
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
    ]

    # Remove excessive empty lines
    cleaned_lines = []
    previous_empty = False

    for line in lines:
        is_empty = not line

        if is_empty and previous_empty:
            continue

        cleaned_lines.append(line)
        previous_empty = is_empty

    return "\n".join(cleaned_lines).strip()


def load_document(file_path: str | Path) -> str:
    """
    Read a document and return cleaned text.

    Args:
        file_path: Path to the document.

    Returns:
        Cleaned extracted text.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file type is unsupported.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # ── PDF ────────────────────────────────────────────────
    if extension == ".pdf":

        reader = PdfReader(str(path))
        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        return clean_text("\n".join(pages))

    # ── DOCX ───────────────────────────────────────────────
    elif extension == ".docx":

        document = Document(str(path))

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        return clean_text("\n".join(paragraphs))

    # ── TXT ────────────────────────────────────────────────
    elif extension == ".txt":

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        return clean_text(text)

    return ""


def load_folder(folder_path: str | Path) -> list[dict]:
    """
    Load every supported document inside a folder and its subfolders.

    Returns:
        [
            {
                "path": "...",
                "filename": "...",
                "text": "..."
            }
        ]
    """

    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(
            f"Folder not found: {folder}"
        )

    documents = []

    for file_path in folder.rglob("*"):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            text = load_document(file_path)

            if text.strip():

                documents.append({
                    "path": str(file_path.resolve()),
                    "filename": file_path.name,
                    "text": text
                })

        except Exception as e:

            print(
                f"[RAG] Could not read "
                f"{file_path.name}: {e}"
            )

    return documents


# ── Test ──────────────────────────────────────────────────

if __name__ == "__main__":

    print("Testing Document Loader")

    # Project root / rag_documents
    project_root = Path(__file__).resolve().parent.parent
    test_folder = project_root / "rag_documents"

    if not test_folder.exists():

        print(
            f"Create this folder and add documents:\n"
            f"{test_folder}"
        )

    else:

        documents = load_folder(test_folder)

        print(f"\nLoaded {len(documents)} document(s).\n")

        for document in documents:

            print("=" * 60)

            print(f"File: {document['filename']}")
            print(f"Path: {document['path']}")

            print("\nPreview:")

            print(document["text"][:1000])

            print()