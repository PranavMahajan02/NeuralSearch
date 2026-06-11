from easyocr_extract import extract_image_text
from florence_extract import extract_text

def extract_hybrid_text(image_path):

    easy_text = extract_image_text(image_path)

    florence_text = extract_text(image_path)

    combined = easy_text + "\n" + florence_text

    return combined