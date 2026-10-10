"""Query embeddings: each model runs once per query, cached by normalized query."""

from functools import lru_cache

from app.ai import embedder


@lru_cache(maxsize=512)
def text_vector(normalized_query: str) -> tuple[float, ...]:
    """MiniLM vector (documents, audio and video transcripts)."""

    return tuple(embedder.embed_text(normalized_query))


@lru_cache(maxsize=512)
def clip_vector(normalized_query: str) -> tuple[float, ...]:
    """CLIP text vector (images and video frames)."""

    return tuple(embedder.embed_clip_text(normalized_query))


def cache_clear() -> None:

    text_vector.cache_clear()
    clip_vector.cache_clear()
