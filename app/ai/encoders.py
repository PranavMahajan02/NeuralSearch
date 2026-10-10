"""Model inference: MiniLM text vectors and CLIP text/image vectors.

Every call holds the model's lock, so concurrent requests take turns on the
GPU instead of contending for it. CLIP text is always truncated to CLIP's
77-token context (a long query used to raise and return HTTP 500 - BUG-07).
"""

from collections.abc import Sequence

from app.ai.model_manager import model_manager
from app.core.timing import waiting_for

CLIP_MAX_TOKENS = 77


def encode_texts(texts: Sequence[str]) -> list[list[float]]:

    model = model_manager.semantic_model

    with waiting_for(model_manager.semantic_lock):
        vectors = model.encode(list(texts), convert_to_numpy=True)

    return [vector.tolist() for vector in vectors]


def encode_clip_text(text: str) -> list[float]:

    import torch

    processor = model_manager.clip_processor
    model = model_manager.clip_model

    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=CLIP_MAX_TOKENS)
    inputs = {key: value.to(model_manager.device) for key, value in inputs.items()}

    with waiting_for(model_manager.clip_lock), torch.no_grad():
        features = model.get_text_features(**inputs)

    return features.cpu().numpy()[0].tolist()


def encode_clip_images(paths: Sequence[str], batch_size: int = 32) -> list[list[float]]:
    """CLIP image vectors, `batch_size` images per forward pass (video frames).
    Same preprocessing as encode_clip_image; the vectors match it to float
    precision (cosine >= 0.9999 on the benchmark frames)."""

    import torch
    from PIL import Image

    processor = model_manager.clip_processor
    model = model_manager.clip_model
    vectors: list[list[float]] = []

    for start in range(0, len(paths), batch_size):
        images = []
        for path in paths[start : start + batch_size]:
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        inputs = processor(images=images, return_tensors="pt")
        inputs = {key: value.to(model_manager.device) for key, value in inputs.items()}

        with waiting_for(model_manager.clip_lock), torch.no_grad():
            features = model.get_image_features(**inputs)

        vectors.extend(features.cpu().numpy().tolist())

    return vectors


def encode_clip_image(path: str) -> list[float]:

    import torch
    from PIL import Image

    processor = model_manager.clip_processor
    model = model_manager.clip_model

    image = Image.open(path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    inputs = {key: value.to(model_manager.device) for key, value in inputs.items()}

    with waiting_for(model_manager.clip_lock), torch.no_grad():
        features = model.get_image_features(**inputs)

    return features.cpu().numpy()[0].tolist()
