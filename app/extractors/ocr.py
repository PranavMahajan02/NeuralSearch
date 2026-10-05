"""PaddleOCR text extraction (one shared model via model_manager)."""

from app.ai.model_manager import model_manager


def extract_text(image_path: str) -> str:

    ocr = model_manager.ocr_model

    with model_manager.ocr_lock:
        result = ocr.ocr(image_path)

    if result is None or result[0] is None:
        return ""

    return " ".join(line[1][0] for line in result[0])
