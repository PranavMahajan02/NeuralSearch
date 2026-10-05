"""Image search over the user's Qdrant points (CLIP vector + OCR text)."""

import re

from rapidfuzz import fuzz

from app.ai.embedder import embed_clip_text
from app.search.common import base_result, group_hits
from app.vectorstore.query import search_points


TOP_K = 5
MIN_FINAL_SCORE = 0.05
QDRANT_LIMIT = 30


def get_filename_score(query, filename):

    query = query.lower()
    filename = re.sub(r"[_\-]+", " ", filename.lower().rsplit(".", 1)[0])

    if query in filename:
        return 1.0

    query_words = set(re.findall(r"\w+", query))
    filename_words = set(re.findall(r"\w+", filename))

    if not query_words:
        return 0.0

    return len(query_words & filename_words) / len(query_words)


def get_content_score(query, content):

    query = query.lower()
    content = content.lower()

    if query in content:
        return 1.0

    query_words = re.findall(r"\w+", query)
    content_words = set(re.findall(r"\w+", content))

    if not query_words:
        return 0.0

    matches = 0

    for word in query_words:
        for c_word in content_words:
            if fuzz.ratio(word, c_word) >= 85:
                matches += 1
                break

    return matches / len(query_words)


def search_images(query, user_id, platform="all"):

    if not query:
        return []

    query = query.strip().lower()

    hits = search_points("image", embed_clip_text(query), user_id, platform, limit=QDRANT_LIMIT)

    results = []

    for _key, group in group_hits(hits).items():

        payload = group["payload"]
        clip_score = group["best"]
        ocr_text = " ".join(group["chunks"])

        filename_score = get_filename_score(query, payload.get("file", ""))
        content_score = get_content_score(query, ocr_text)

        if content_score > 0:
            score = 0.50 * content_score + 0.30 * filename_score + 0.20 * clip_score
        elif filename_score > 0:
            score = 0.60 * filename_score + 0.40 * clip_score
        else:
            score = clip_score

        if score < MIN_FINAL_SCORE:
            continue

        result = base_result(payload, "image", score)
        result.update({
            "filename_score": filename_score,
            "ocr_score": content_score,
            "clip_score": clip_score,
            "ocr_text": ocr_text,
        })
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)

    return results[:TOP_K]
