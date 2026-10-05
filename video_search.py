"""Video search over the user's Qdrant points.

BUG-02: semantic_score is the best transcript-point score of the source and
content_score is computed from those transcript chunks; clip_score is the
best frame score of the source. Transcript and frame hits are joined on
(platform, source_id), not the filename.
"""

import re

from app.ai.embedder import embed_clip_text, embed_text
from app.search.common import base_result, group_hits, source_key
from app.vectorstore.query import search_points


TOP_K = 5
MIN_SCORE = 0.05
TRANSCRIPT_LIMIT = 100
FRAME_LIMIT = 1000


def get_filename_score(query, filename):

    filename = re.sub(r"[_\-]+", " ", filename.lower().rsplit(".", 1)[0])

    if query == filename:
        return 1.0

    if query in filename:
        return 0.95

    query_words = set(re.findall(r"\w+", query))
    filename_words = set(re.findall(r"\w+", filename))

    if not query_words:
        return 0

    return len(query_words & filename_words) / len(query_words)


def get_content_score(query, transcript):

    transcript = str(transcript).lower()

    if query in transcript:
        return 1.0

    query_words = set(re.findall(r"\w+", query))
    transcript_words = set(re.findall(r"\w+", transcript))

    if not query_words:
        return 0

    return len(query_words & transcript_words) / len(query_words)


def search_video(query, user_id, platform="all"):

    if not query:
        return []

    query = query.strip().lower()

    transcript_groups = group_hits(
        search_points("video", embed_text(query), user_id, platform, limit=TRANSCRIPT_LIMIT)
    )

    clip_scores = {}
    frame_payloads = {}

    for point in search_points("video_frame", embed_clip_text(query), user_id, platform, limit=FRAME_LIMIT):
        payload = point.payload or {}
        key = source_key(payload)
        clip_scores[key] = max(clip_scores.get(key, 0.0), float(point.score))
        frame_payloads.setdefault(key, payload)

    results = []

    for key in list(transcript_groups) + [k for k in frame_payloads if k not in transcript_groups]:

        group = transcript_groups.get(key)
        payload = group["payload"] if group else frame_payloads[key]

        semantic_score = group["best"] if group else 0.0
        content_score = get_content_score(query, " ".join(group["chunks"])) if group else 0.0
        clip_score = clip_scores.get(key, 0.0)
        filename_score = get_filename_score(query, payload.get("file", ""))

        if filename_score > 0:
            final_score = 0.50 * filename_score + 0.20 * content_score + 0.15 * semantic_score + 0.15 * clip_score
        elif content_score > 0:
            final_score = 0.60 * content_score + 0.25 * semantic_score + 0.15 * clip_score
        else:
            final_score = 0.60 * semantic_score + 0.40 * clip_score

        if final_score < MIN_SCORE:
            continue

        result = base_result(payload, "video", final_score)
        result.update({
            "filename_score": float(filename_score),
            "content_score": float(content_score),
            "semantic_score": float(semantic_score),
            "clip_score": float(clip_score),
            "preview": (group["chunks"][0] if group and group["chunks"] else "")[:300],
        })
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)

    return results[:TOP_K]
