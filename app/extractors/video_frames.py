"""Sample one frame every `interval` seconds (frame numbers 0, step, 2*step, ...
with step = int(fps * interval)) and save them as JPEGs.

The visual-video calibration (app/search/frame_null.py) depends on these exact
frames, so the sampled frame NUMBERS are part of the contract.

Seek per sample instead of decoding every frame: OpenCV's FFmpeg backend jumps
to the keyframe before the target and decodes forward to the exact frame, so
only about half a GOP is decoded per sample instead of the whole 5-second
interval. Measured on the benchmark videos: 4.8-6.6x faster, pixel-identical
frames (docs/perf/RESULTS.md). Videos whose frame count is unknown (or a seek
that fails mid-way) fall back to the sequential decode.
"""

import logging
import os
from typing import List

import cv2


logger = logging.getLogger("cogniseek.extractors.frames")

INTERVAL_SECONDS = 5


def sample_step(fps: float, interval: float = INTERVAL_SECONDS) -> int:
    """Frames between samples. Corrupt or unreadable videos report 0 fps:
    sample every frame instead of dividing by zero."""

    return max(1, int((fps or 0) * interval))


def sample_frame_numbers(fps: float, frame_count: int, interval: float = INTERVAL_SECONDS) -> List[int]:

    return list(range(0, max(0, int(frame_count)), sample_step(fps, interval)))


def _save(frame, output_folder: str, number: int) -> str:

    path = os.path.join(output_folder, f"frame_{number}.jpg")
    cv2.imwrite(path, frame)
    return path


def _sequential(video_path: str, output_folder: str, interval: float) -> List[str]:
    """Decode every frame and keep each step-th one (the original method)."""

    os.makedirs(output_folder, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    step = sample_step(cap.get(cv2.CAP_PROP_FPS), interval)
    saved, count = [], 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if count % step == 0:
            saved.append(_save(frame, output_folder, len(saved)))
        count += 1

    cap.release()
    return saved


def _probe(cap) -> tuple:
    """(fps, frame count) as reported by the container."""

    return cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)


def extract_frames(video_path: str, output_folder: str, interval: float = INTERVAL_SECONDS) -> List[str]:

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps, count = _probe(cap)

    if fps <= 0 or count <= 0:
        cap.release()
        return _sequential(video_path, output_folder, interval)

    saved = []
    numbers = sample_frame_numbers(fps, count, interval)

    for number in numbers:
        if not cap.set(cv2.CAP_PROP_POS_FRAMES, number):
            break
        ok, frame = cap.read()
        if not ok:
            break
        saved.append(_save(frame, output_folder, len(saved)))

    cap.release()

    if not saved and numbers:
        logger.debug("seeking failed for %s; decoding sequentially", os.path.basename(video_path))
        return _sequential(video_path, output_folder, interval)

    return saved
