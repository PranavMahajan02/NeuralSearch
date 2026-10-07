"""Add the per-video null distribution and frame timestamps to already-indexed video frames.

    python scripts/backfill_video_null.py --dry-run
    python scripts/backfill_video_null.py

New videos get these fields at index time (app/services/indexers/video_indexer.py).
For every user's video this reads the stored frame vectors (nothing is re-downloaded or
re-embedded), computes null_mean / null_std (app/search/frame_null.py) and sets them, plus
frame_time_s, on the video's frame points. Only payload fields are added; vectors are untouched.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qdrant_client.models import FieldCondition, Filter, MatchValue  # noqa: E402

from app.search.frame_null import frame_time_s, null_stats  # noqa: E402
from app.vectorstore.client import get_client  # noqa: E402
from app.vectorstore.config import collection_for_type  # noqa: E402


def backfill(dry_run: bool) -> int:

    client = get_client()
    collection = collection_for_type("video_frame")
    videos = defaultdict(list)
    offset = None

    while True:
        points, offset = client.scroll(collection, limit=500, with_vectors=True, with_payload=True, offset=offset)
        for p in points:
            payload = p.payload or {}
            videos[(payload.get("user_id"), payload.get("platform"), payload.get("source_id"))].append(p)
        if offset is None:
            break

    for (user_id, platform, source_id), points in videos.items():
        mean, std = null_stats([p.vector for p in points])
        print(f"user {str(user_id)[:8]}... {platform} video: {len(points)} frames, null mean {mean:.4f} std {std:.4f}")
        if dry_run:
            continue
        for p in points:
            client.set_payload(
                collection,
                payload={"null_mean": mean, "null_std": std,
                         "frame_time_s": frame_time_s((p.payload or {}).get("frame_number"))},
                points=[p.id],
                wait=False,
            )

    return len(videos)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    print(f"{backfill(parser.parse_args().dry_run)} video(s)")
