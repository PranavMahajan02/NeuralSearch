"""Video -> transcript chunks (MiniLM, collection: video)
         + sampled frames (CLIP, collection: video_frames).

BUG-02 (storage side): the transcript text is stored on every "video" point
as `chunk`, so search can score spoken content.
"""

import shutil
import uuid
from pathlib import Path
from typing import List

from app.ai.embedder import embed_clip_image, embed_texts
from app.core.config import settings
from app.search.frame_null import frame_time_s, null_stats
from app.services.index_store import IndexPoint
from app.services.indexers.document_indexer import chunk_text


CHUNK_SIZE = 500


def extract_video_transcript(path: str) -> str:

    from app.extractors.video_extract import extract_video_text

    return extract_video_text(path) or ""


def extract_frames(path: str, output_folder: str) -> List[str]:

    from app.extractors.video_frames import extract_frames as extract

    return extract(path, output_folder)


def build_video_points(path: str, temp_dir=None) -> List[IndexPoint]:

    points: List[IndexPoint] = []

    transcript = extract_video_transcript(path)

    if transcript.strip():
        chunks = chunk_text(transcript, CHUNK_SIZE)
        vectors = embed_texts(chunks)
        points.extend(
            IndexPoint(type="video", vector=vector, chunk_index=index, chunk=chunk)
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        )

    # Private frame folder per call (no shared temp_frames - BUG-18).
    frames_dir = Path(temp_dir or settings.TEMP_DIR) / f"frames-{uuid.uuid4().hex}"

    try:
        vectors = [embed_clip_image(frame_path) for frame_path in extract_frames(path, str(frames_dir))]

        # Per-video null (app/search/frame_null.py): stored on every frame point.
        null_mean, null_std = null_stats(vectors)

        for number, vector in enumerate(vectors):
            points.append(
                IndexPoint(
                    type="video_frame",
                    vector=vector,
                    chunk_index=number,
                    chunk=f"Frame {number}",
                    frame_number=number,
                    extra={"frame_time_s": frame_time_s(number), "null_mean": null_mean, "null_std": null_std},
                )
            )
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)

    return points
