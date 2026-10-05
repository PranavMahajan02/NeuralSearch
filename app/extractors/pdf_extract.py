"""PDF text: the text layer, plus per-page OCR where the text layer is not enough.

A page is OCR'd when (up to settings.OCR_MAX_PAGES pages per file):
  - its text layer has fewer than MIN_ALNUM alphanumeric characters (scanned), or
  - its text is mostly noise (broken encodings: few word-like tokens), or
  - images cover at least IMAGE_COVERAGE_OCR of the page.

The last rule is what scanned ID cards and certificates need: e.g. an Aadhaar
PDF has ~390 characters of text (numbers, Hindi) but the words that identify
it ("Aadhaar", "Government of India") are only inside images. For such pages
the OCR text is appended to the text layer; for scanned/noisy pages it
replaces it.
"""

import logging
import os
import re
import tempfile

from app.core.config import settings


logger = logging.getLogger("cogniseek.extractors.pdf")

MIN_ALNUM = 30
IMAGE_COVERAGE_OCR = 0.40
MIN_WORDLIKE_RATIO = 0.5

_ALNUM = re.compile(r"[A-Za-z0-9]")
_LATIN_TOKEN = re.compile(r"[A-Za-z]{2,}")
_VOWEL = re.compile(r"[aeiouyAEIOUY]")
_CONSONANT_RUN = re.compile(r"[^aeiouyAEIOUY]{5,}")


def alnum_count(text: str) -> int:

    return len(_ALNUM.findall(text or ""))


def is_noise(text: str) -> bool:
    """True when most Latin tokens don't look like words (no vowel, or long
    consonant runs) - typical of PDFs with broken font encodings."""

    tokens = _LATIN_TOKEN.findall(text or "")

    if len(tokens) < 5:
        return False

    wordlike = sum(1 for t in tokens if _VOWEL.search(t) and not _CONSONANT_RUN.search(t))

    return wordlike / len(tokens) < MIN_WORDLIKE_RATIO


def image_coverage(page) -> float:
    """Share of the page area covered by embedded images (0..1)."""

    area = float(page.width * page.height) or 1.0
    covered = 0.0

    for image in page.images:
        width = max(0.0, min(image["x1"], page.width) - max(image["x0"], 0))
        height = max(0.0, min(image["bottom"], page.height) - max(image["top"], 0))
        covered += width * height

    return min(1.0, covered / area)


def ocr_reason(text: str, coverage: float):

    if alnum_count(text) < MIN_ALNUM:
        return "scanned"
    if is_noise(text):
        return "noise"
    if coverage >= IMAGE_COVERAGE_OCR:
        return "image-heavy"
    return None


def render_page(pdf_path: str, page_number: int, output_dir: str) -> str:
    """Render one page (1-based) to a JPEG with Poppler; returns its path."""

    from pdf2image import convert_from_path

    images = convert_from_path(
        pdf_path,
        dpi=200,
        first_page=page_number,
        last_page=page_number,
        poppler_path=settings.POPPLER_PATH or None
    )

    path = os.path.join(output_dir, f"page_{page_number}.jpg")
    images[0].save(path, "JPEG")

    return path


def ocr_image(path: str) -> str:

    from app.extractors.ocr import extract_text

    return extract_text(path) or ""


def extract_text(pdf_path: str) -> str:

    import pdfplumber

    parts = []
    ocr_pages = 0
    ocr_failed = False

    with pdfplumber.open(pdf_path) as pdf, tempfile.TemporaryDirectory(prefix="pdf-ocr-") as tmp:

        for number, page in enumerate(pdf.pages, start=1):

            text = page.extract_text() or ""
            reason = ocr_reason(text, image_coverage(page))

            if reason and not ocr_failed and ocr_pages < settings.OCR_MAX_PAGES:

                try:
                    ocr_text = ocr_image(render_page(pdf_path, number, tmp))
                    ocr_pages += 1
                except Exception as error:
                    # e.g. Poppler missing: keep the text layer, stop trying.
                    ocr_failed = True
                    logger.warning("OCR unavailable for %s (%s); using the text layer only",
                                   os.path.basename(pdf_path), type(error).__name__)
                    ocr_text = ""

                logger.debug("page %d of %s: OCR (%s) %d -> %d alnum chars",
                             number, os.path.basename(pdf_path), reason, alnum_count(text), alnum_count(ocr_text))

                if reason == "image-heavy":
                    text = f"{text}\n{ocr_text}" if ocr_text else text
                elif alnum_count(ocr_text) > alnum_count(text) or reason == "noise":
                    text = ocr_text or text

            parts.append(text)

    if ocr_pages:
        logger.info("OCR'd %d page(s) of %s", ocr_pages, os.path.basename(pdf_path))

    return "\n".join(parts)
