from easyocr_extract import extract_image_text as easyocr_ocr
from florence2_test.florence_extract import extract_text as florence_ocr


def extract_best_text(image_path):

    print("Running EasyOCR...")
    easy_text = easyocr_ocr(image_path)

    print("Running Florence-2...")
    florence_text = florence_ocr(image_path)

    # Remove duplicate lines
    merged_text = easy_text + "\n" + florence_text

    return merged_text