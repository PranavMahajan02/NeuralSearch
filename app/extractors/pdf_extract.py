"""PDF text: pdfplumber first, OCR fallback for scanned PDFs."""

import logging
import os
import tempfile

from app.core.config import settings


logger = logging.getLogger("cogniseek.extractors.pdf")


def extract_text(pdf_path: str) -> str:

    import pdfplumber

    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if text.strip():
        return text

    logger.info("Scanned PDF, running OCR: %s", os.path.basename(pdf_path))

    from pdf2image import convert_from_path

    from app.extractors.ocr import extract_text as ocr_text

    pages = convert_from_path(pdf_path, poppler_path=settings.POPPLER_PATH or None)

    parts = []

    # Private temp dir: concurrent jobs never share page images.
    with tempfile.TemporaryDirectory(prefix="pdf-ocr-") as tmp:
        for number, page in enumerate(pages):
            page_file = os.path.join(tmp, f"page_{number}.jpg")
            page.save(page_file, "JPEG")
            parts.append(ocr_text(page_file))

    return "\n".join(parts)
