"""Per-candidate calibration of embedding similarity.

Raw cosine scores are not comparable across queries or models: CLIP gives
almost every (text, image) pair 0.18-0.30, so a fixed threshold either lets
everything through or nothing. Instead we ask, for each candidate vector:

    how much more does it match THIS query than it matches generic,
    content-free prompts ("a photo", "a document", ...)?

    margin = cos(query, candidate) - mean(top-3 cos(neutral_i, candidate))

A tiger photo matches "tiger" far better than "a photo" (large margin); for a
nonsense query the margin is near or below zero for every candidate. The
neutral prompt vectors are computed once and cached.
"""

from functools import lru_cache

import numpy as np

from app.ai import embedder


TEXT_NEUTRAL_PROMPTS = (
    "document", "a text file", "notes", "a page of text", "information",
    "some content", "a file", "general text about a topic", "a report", "a list",
)

CLIP_NEUTRAL_PROMPTS = (
    "a photo", "an image", "a picture", "a photograph of something", "a screenshot",
    "a frame from a video", "an object", "a scene", "a picture with text", "a person",
)

TOP_NEUTRAL = 3


def _unit_rows(matrix: np.ndarray) -> np.ndarray:

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    return matrix / norms


@lru_cache(maxsize=1)
def text_neutral_matrix() -> np.ndarray:

    return _unit_rows(np.asarray(embedder.embed_texts(list(TEXT_NEUTRAL_PROMPTS)), dtype=np.float32))


@lru_cache(maxsize=1)
def clip_neutral_matrix() -> np.ndarray:

    return _unit_rows(np.asarray([embedder.embed_clip_text(p) for p in CLIP_NEUTRAL_PROMPTS], dtype=np.float32))


def margins(query_scores, candidate_vectors, neutral: np.ndarray) -> np.ndarray:
    """query cosine minus the mean of the 3 best neutral-prompt cosines."""

    if len(candidate_vectors) == 0:
        return np.zeros(0, dtype=np.float32)

    vectors = _unit_rows(np.asarray(candidate_vectors, dtype=np.float32))
    neutral_scores = vectors @ neutral.T                       # (n_candidates, n_prompts)
    k = min(TOP_NEUTRAL, neutral_scores.shape[1])
    baseline = np.sort(neutral_scores, axis=1)[:, -k:].mean(axis=1)

    return np.asarray(query_scores, dtype=np.float32) - baseline


def cache_clear() -> None:

    text_neutral_matrix.cache_clear()
    clip_neutral_matrix.cache_clear()
