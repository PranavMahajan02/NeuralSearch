"""Per-video null distribution for frame (CLIP) evidence.

The best frame of a video is the max over N noisy frame margins, so it rises
with N and with how "generic" the footage is. Each video therefore gets its
own null: the best-frame margin of NULL_PROMPTS (things unrelated to any query)
over ALL its frames, summarised as mean and standard deviation. A query's
best-frame margin is then scored as z = (max - null_mean) / null_std, which is
comparable across videos of any length (docs/eval/phase6c-video-gate.md).

The null depends only on the video, so it is computed once at index time (and
by scripts/backfill_video_null.py for older videos) and stored on every frame
point; a query needs only its retrieved frames.
"""

from functools import lru_cache
from typing import Optional, Sequence, Tuple

import numpy as np

# Seconds between sampled frames (app/extractors/video_frames.py, interval=5): 12 frames per minute.
FRAME_INTERVAL_S = 5

NULL_PROMPTS = (
    "a bicycle", "a sandwich", "a guitar", "a umbrella", "a clock", "a shoe",
    "a bridge at night", "a train", "a cup of tea", "a keyboard", "a football", "a tractor in a field",
)


@lru_cache(maxsize=1)
def null_matrix() -> np.ndarray:

    from app.ai import embedder

    rows = np.asarray([embedder.embed_clip_text(p) for p in NULL_PROMPTS], dtype=np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def null_stats(frame_vectors: Sequence[Sequence[float]]) -> Tuple[Optional[float], Optional[float]]:
    """(mean, std) of the best-frame margin of each null prompt over this video's frames."""

    from app.search.calibration import clip_neutral_matrix, margins

    if len(frame_vectors) == 0:
        return None, None

    frames = np.asarray(frame_vectors, dtype=np.float32)
    frames = frames / np.maximum(np.linalg.norm(frames, axis=1, keepdims=True), 1e-12)
    neutral = clip_neutral_matrix()

    best = [float(margins(frames @ prompt, frames, neutral).max()) for prompt in null_matrix()]

    return float(np.mean(best)), float(max(np.std(best), 1e-3))


def frame_time_s(frame_number: Optional[int]) -> Optional[int]:

    return None if frame_number is None else int(frame_number) * FRAME_INTERVAL_S


def format_timestamp(seconds: Optional[int]) -> Optional[str]:
    """75 -> '1:15', 3725 -> '1:02:05'."""

    if seconds is None:
        return None
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
