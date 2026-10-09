"""Documents -> text chunks -> MiniLM vectors (collection: text)."""

import os
from typing import List

from app.ai.embedder import embed_texts
from app.config.file_types import TEXT_DOCUMENTS
from app.core.config import settings
from app.services.index_store import IndexPoint, Points
from app.core.timing import span


CHUNK_SIZE = 1000


def extract_document_text(path: str) -> str:

    with span("extract_text"):
        return _extract(path)


def _extract(path: str) -> str:

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
    """No text -> no points (the ledger records 'no_content').

    Text beyond MAX_TEXT_CHARS_PER_FILE / MAX_CHUNKS_PER_FILE is dropped and
    the result carries a 'truncated' note for the ledger."""

    text = extract_document_text(path) or ""

    if not text.strip():
        return Points()

    limit = min(settings.MAX_TEXT_CHARS_PER_FILE, settings.MAX_CHUNKS_PER_FILE * CHUNK_SIZE)
    note = None

    if len(text) > limit:
        note = f"truncated: first {limit:,} of {len(text):,} characters indexed"
        text = text[:limit]

    chunks = chunk_text(text, CHUNK_SIZE)
    vectors = embed_texts(chunks)

    return Points(
        (IndexPoint(type="document", vector=vector, chunk_index=index, chunk=chunk)
         for index, (chunk, vector) in enumerate(zip(chunks, vectors))),
        note=note
    )
