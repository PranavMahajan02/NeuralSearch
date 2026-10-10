"""The single seam between the app and the embedding models.

Indexers and search call these functions only. Tests replace `backend` with a
deterministic fake, so no model is ever loaded in the test suite.
"""

from collections.abc import Sequence

from app.core.timing import span


class ModelEmbedder:
    """Real models, imported lazily (they pull in torch/transformers)."""

    def text(self, texts: Sequence[str]) -> list[list[float]]:

        from app.ai.encoders import encode_texts

        return encode_texts(texts)

    def clip_text(self, text: str) -> list[float]:

        from app.ai.encoders import encode_clip_text

        return encode_clip_text(text)

    def clip_image(self, path: str) -> list[float]:

        from app.ai.encoders import encode_clip_image

        return encode_clip_image(path)

    def clip_images(self, paths: Sequence[str]) -> list[list[float]]:

        from app.ai.encoders import encode_clip_images

        return encode_clip_images(paths)


backend = ModelEmbedder()


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """MiniLM (384-d) vectors for documents, audio and video transcripts."""

    if not texts:
        return []

    with span("minilm"):
        return backend.text(texts)


def embed_text(text: str) -> list[float]:

    return embed_texts([text])[0]


def embed_clip_text(text: str) -> list[float]:
    """CLIP (512-d) text vector, for image and video-frame search."""

    return backend.clip_text(text)


def embed_clip_image(path: str) -> list[float]:

    with span("clip_image"):
        return backend.clip_image(path)


def embed_clip_images(paths: Sequence[str]) -> list[list[float]]:
    """Batched CLIP image vectors (video frames). Backends without a batch
    method (test fakes) are called per image."""

    if not paths:
        return []

    with span("clip_image"):
        batch = getattr(backend, "clip_images", None)
        if batch is not None:
            return batch(list(paths))
        return [backend.clip_image(path) for path in paths]
