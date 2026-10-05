"""Images -> one CLIP vector + OCR text (collection: image)."""

from typing import List

from app.ai.embedder import embed_clip_image
from app.services.index_store import IndexPoint


def extract_image_text(path: str) -> str:

    from paddle_extract import extract_text as paddle_ocr

    return paddle_ocr(path) or ""


def build_image_points(path: str, temp_dir=None) -> List[IndexPoint]:

    vector = embed_clip_image(path)
    ocr_text = extract_image_text(path)

    return [IndexPoint(type="image", vector=vector, chunk_index=0, chunk=ocr_text)]
