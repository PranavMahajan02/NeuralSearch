import os
import pdfplumber

from pdf2image import convert_from_path

from paddle_extract import (
    extract_text as paddle_ocr
)

POPPLER_PATH = (
    r"C:\Users\Pranav Mahajan\Downloads"
    r"\Release-26.02.0-0"
    r"\poppler-26.02.0"
    r"\Library\bin"
)


def extract_text(pdf_path):

    text = ""

    # -------------------------
    # Try pdfplumber first
    # -------------------------

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    # -------------------------
    # If text found
    # -------------------------

    if text.strip():

        print(
            "PDF text extracted using pdfplumber"
        )

        return text

    # -------------------------
    # OCR fallback
    # -------------------------

    print(
        "Scanned PDF detected."
    )

    print(
        "Running PaddleOCR..."
    )

    pages = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH
    )

    ocr_text = ""

    for i, page in enumerate(pages):

        temp_file = (
            f"temp_page_{i}.jpg"
        )

        page.save(
            temp_file,
            "JPEG"
        )

        ocr_text += (
            paddle_ocr(temp_file)
            + "\n"
        )

        os.remove(temp_file)

    return ocr_text