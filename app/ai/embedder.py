"""The single seam between the app and the embedding models.

Indexers and search call these functions only. Tests replace `backend` with a
deterministic fake, so no model is ever loaded in the test suite.
"""

from typing import List, Sequence


class ModelEmbedder:
    """Real models, imported lazily (they pull in torch/transformers)."""

    def text(self, texts: Sequence[str]) -> List[List[float]]:

        from embeddings import get_embeddings

        vectors = get_embeddings(list(texts))

        return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]

    def clip_text(self, text: str) -> List[float]:

        from clip_extract import get_text_embedding

        return list(get_text_embedding(text))

    def clip_image(self, path: str) -> List[float]:

        from clip_extract import get_image_embedding

        return list(get_image_embedding(path))


backend = ModelEmbedder()


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """MiniLM (384-d) vectors for documents, audio and video transcripts."""

    if not texts:
        return []

    return backend.text(texts)


def embed_text(text: str) -> List[float]:

    return embed_texts([text])[0]


def embed_clip_text(text: str) -> List[float]:
    """CLIP (512-d) text vector, for image and video-frame search."""

    return backend.clip_text(text)


def embed_clip_image(path: str) -> List[float]:

    return backend.clip_image(path)
