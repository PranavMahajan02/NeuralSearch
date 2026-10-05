"""Audio search over the user's Qdrant points (transcript chunks)."""

import re

from app.ai.embedder import embed_text
from app.search.common import base_result
from app.vectorstore.query import search_points


TOP_K = 5
MIN_SCORE = 0.15
QDRANT_LIMIT = 100


def get_filename_score(query, filename):

    query = query.lower()
    filename = filename.lower().rsplit(".", 1)[0]

    if query == filename:
        return 1.0

    if query in filename:
        return 0.9

    query_words = set(re.findall(r"\w+", query))
    filename_words = set(re.findall(r"\w+", filename))

    if not query_words:
        return 0

    return len(query_words & filename_words) / len(query_words)


def get_content_score(query, transcript):

    query = query.lower()
    transcript = transcript.lower()

    if query in transcript:
        return 1.0

    query_words = set(re.findall(r"\w+", query))
    transcript_words = set(re.findall(r"\w+", transcript))

    if not query_words:
        return 0

    return len(query_words & transcript_words) / len(query_words)


def search_audio(query, user_id, platform="all"):

    if not query:
        return []

    query = query.strip().lower()

    hits = search_points("audio", embed_text(query), user_id, platform, limit=QDRANT_LIMIT)

    best = {}

    # Score each chunk; keep the best chunk per source (not per basename).
    for point in hits:

        payload = point.payload or {}
        semantic_score = float(point.score)
        filename_score = get_filename_score(query, payload.get("file", ""))
        content_score = get_content_score(query, payload.get("chunk", ""))

        final_score = 0.20 * filename_score + 0.40 * content_score + 0.40 * semantic_score

        if final_score < MIN_SCORE:
            continue

        key = (payload.get("platform"), payload.get("source_id"))

        if key in best and best[key]["score"] >= final_score:
            continue

        result = base_result(payload, "audio", final_score)
        result.update({
            "filename_score": filename_score,
            "content_score": content_score,
            "semantic_score": semantic_score,
            "preview": payload.get("chunk", "")[:300],
        })
        best[key] = result

    return sorted(best.values(), key=lambda r: r["score"], reverse=True)[:TOP_K]
