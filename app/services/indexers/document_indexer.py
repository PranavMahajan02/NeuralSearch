"""Documents -> text chunks -> MiniLM vectors (collection: text)."""

import os
from typing import List

from app.ai.embedder import embed_texts
from app.config.file_types import TEXT_DOCUMENTS
from app.services.index_store import IndexPoint


CHUNK_SIZE = 1000


def extract_document_text(path: str) -> str:

    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        from app.extractors.pdf_extract import extract_text
        return extract_text(path)

    if extension == ".docx":
        from app.extractors.docx_extract import extract_docx
        return extract_docx(path)

    if extension == ".pptx":
        from app.extractors.pptx_extract import extract_pptx
        return extract_pptx(path)

    if extension == ".csv":
        from app.services.indexers.csv_extract import extract_csv
        return extract_csv(path)

    if extension in TEXT_DOCUMENTS:   # includes .md / .markdown
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    raise ValueError(f"Unsupported document type: {extension or 'none'}")


def chunk_text(text: str, size: int) -> List[str]:

    return [text[i:i + size] for i in range(0, len(text), size)]


def build_document_points(path: str, temp_dir=None) -> List[IndexPoint]:
    """No text -> no points (the ledger records 'no_content')."""

    text = extract_document_text(path) or ""

    if not text.strip():
        return []

    chunks = chunk_text(text, CHUNK_SIZE)
    vectors = embed_texts(chunks)

    return [
        IndexPoint(type="document", vector=vector, chunk_index=index, chunk=chunk)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
