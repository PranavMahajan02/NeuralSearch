import sys
import os

# Add parent folder (omniseach-ai) to Python path
sys.path.append(
    os.path.abspath("..")
)

from florence_extract import extract_text as florence_extract
from easyocr_extract import extract_image_text as easyocr_extract

images = [
    "../data/Hall ticket.jpeg",
    "../data/india_post.jpeg",
    "../data/mit_receipt.jpeg",
    "../data/medical bill.jpeg"
]

for image_path in images:

    print("\n" + "=" * 80)
    print("FILE:", image_path)
    print("=" * 80)

    print("\nEASYOCR:")
    try:
        print(
            easyocr_extract(image_path)
        )
    except Exception as e:
        print(
            f"EasyOCR Error: {e}"
        )

    print("\nFLORENCE:")
    try:
        print(
            florence_extract(image_path)
        )
    except Exception as e:
        print(
            f"Florence Error: {e}"
        )