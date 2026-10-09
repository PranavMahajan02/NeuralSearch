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
from app.core.timing import span


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


def page_runs(numbers):
    """[1, 2, 3, 7, 9, 10] -> [(1, 3), (7, 7), (9, 10)] (contiguous, ascending)."""

    runs = []
    for number in sorted(numbers):
        if runs and number == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], number)
        else:
            runs.append((number, number))
    return runs


def render_pages(pdf_path: str, numbers, output_dir: str) -> dict:
    """Render pages (1-based) to JPEGs with Poppler: {page number: path}.

    One pdftoppm call per contiguous run of pages (pdf2image splits a run over
    up to 4 processes) instead of one call per page: the same pixels, ~40% less
    time on a 20-page run (docs/perf/RESULTS.md)."""

    from pdf2image import convert_from_path

    paths = {}

    with span("pdf_render"):
        for first, last in page_runs(numbers):
            images = convert_from_path(
                pdf_path,
                dpi=200,
                first_page=first,
                last_page=last,
                thread_count=min(4, last - first + 1),
                poppler_path=settings.POPPLER_PATH or None
            )
            for number, image in zip(range(first, last + 1), images):
                path = os.path.join(output_dir, f"page_{number}.jpg")
                image.save(path, "JPEG")
                paths[number] = path

    return paths


def render_page(pdf_path: str, page_number: int, output_dir: str) -> str:
    """Render one page (1-based) to a JPEG; returns its path."""

    return render_pages(pdf_path, [page_number], output_dir)[page_number]


def ocr_image(path: str) -> str:

    from app.extractors.ocr import extract_text

    return extract_text(path) or ""


def merge_ocr(text: str, ocr_text: str, reason: str) -> str:

    if reason == "image-heavy":
        return f"{text}\n{ocr_text}" if ocr_text else text
    if alnum_count(ocr_text) > alnum_count(text) or reason == "noise":
        return ocr_text or text
    return text


def extract_text(pdf_path: str) -> str:
    """1. text layer + OCR decision per page; 2. render the chosen pages (at
    most OCR_MAX_PAGES, first ones first) in contiguous runs; 3. OCR and merge."""

    import pdfplumber

    texts, reasons = [], {}

    with pdfplumber.open(pdf_path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            texts.append(text)
            reason = ocr_reason(text, image_coverage(page))
            if reason and len(reasons) < settings.OCR_MAX_PAGES:
                reasons[number] = reason

    if not reasons:
        return "\n".join(texts)

    name = os.path.basename(pdf_path)
    ocr_pages = 0

    with tempfile.TemporaryDirectory(prefix="pdf-ocr-") as tmp:

        try:
            rendered = render_pages(pdf_path, list(reasons), tmp)
        except Exception as error:
            # e.g. Poppler missing: keep the text layer.
            logger.warning("OCR unavailable for %s (%s); using the text layer only", name, type(error).__name__)
            return "\n".join(texts)

        for number, reason in reasons.items():
            try:
                ocr_text = ocr_image(rendered[number])
            except Exception as error:
                logger.warning("OCR failed for %s (%s); using the text layer for the rest", name, type(error).__name__)
                break
            ocr_pages += 1
            text = texts[number - 1]
            logger.debug("page %d of %s: OCR (%s) %d -> %d alnum chars",
                         number, name, reason, alnum_count(text), alnum_count(ocr_text))
            texts[number - 1] = merge_ocr(text, ocr_text, reason)

    if ocr_pages:
        logger.info("OCR'd %d page(s) of %s", ocr_pages, name)

    return "\n".join(texts)
