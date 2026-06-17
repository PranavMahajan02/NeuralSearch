import os

from extract import extract_text
from docx_extract import extract_docx
from pptx_extract import extract_pptx
from txt_extract import extract_txt

from paddle_extract import (
    extract_text as paddle_ocr
)

test_folder = "test"

print("\nTesting File Extraction...\n")

for filename in os.listdir(test_folder):

    file_path = os.path.join(
        test_folder,
        filename
    )

    print("\n" + "=" * 50)
    print(f"FILE: {filename}")
    print("=" * 50)

    text = ""

    try:

        # -----------------------
        # PDF
        # -----------------------
        if filename.lower().endswith(".pdf"):

            print("Type: PDF")

            text = extract_text(
                file_path
            )

        # -----------------------
        # DOCX
        # -----------------------
        elif filename.lower().endswith(".docx"):

            print("Type: DOCX")

            text = extract_docx(
                file_path
            )

        # -----------------------
        # PPTX
        # -----------------------
        elif filename.lower().endswith(".pptx"):

            print("Type: PPTX")

            text = extract_pptx(
                file_path
            )

        # -----------------------
        # TXT
        # -----------------------
        elif filename.lower().endswith(".txt"):

            print("Type: TXT")

            text = extract_txt(
                file_path
            )

        # -----------------------
        # IMAGE OCR
        # -----------------------
        elif filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):

            print("Type: IMAGE")

            text = paddle_ocr(
                file_path
            )

        else:

            print(
                "Unsupported format"
            )

            continue

        # -----------------------
        # RESULTS
        # -----------------------

        if not text.strip():

            print(
                "❌ No text extracted"
            )

        else:

            print(
                f"✅ Extracted {len(text)} characters"
            )

            print("\nPreview:\n")

            print(
                text[:500]
            )

    except Exception as e:

        print(
            f"❌ ERROR: {e}"
        )

print("\n\nTesting Complete.")