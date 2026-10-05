"""Document search over the user's Qdrant points.

Scores are computed per source (platform, source_id) from that source's hits
only (BUG-20: no more basename-keyed global caches). Weights and thresholds
are unchanged; Phase 4 tunes them.
"""

import re

from rapidfuzz import fuzz, process

from app.ai.embedder import embed_text
from app.search.common import base_result, group_hits, title_name
from app.vectorstore.query import search_points


FUZZY_WORD_THRESHOLD = 85   # Min similarity score for a word match (0-100)
MIN_WORD_LENGTH = 4         # Ignore words shorter than this (reduces noise)
SEMANTIC_THRESHOLD = 0.35   # Min cosine similarity for semantic search
MIN_FINAL_SCORE = 0.30
TOP_K = 10
QDRANT_LIMIT = 500


def get_title_score(query, filename):

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


def get_content_score(query, content):

    if query.lower() in content.lower():
        return 1.0

    query_words = set(re.findall(r"\w+", query.lower()))
    content_words = set(re.findall(r"\w+", content.lower()))

    if not query_words:
        return 0.0

    matches = 0

    for q_word in query_words:

        if q_word in content_words:
            matches += 1
            continue

        for c_word in content_words:
            if abs(len(q_word) - len(c_word)) <= 2 and fuzz.ratio(q_word, c_word) >= 88:
                matches += 1
                break

    return matches / len(query_words)


def fuzzy_match_chunk(chunk: str, query_words: list) -> int:
    """Best fuzzy match (0-100) between any query word and any chunk word.

    Punctuation is stripped, chunk words must be within +-30% of the query
    word's length, and whole-word fuzz.ratio is used (not partial_ratio).
    """

    chunk_words = [re.sub(r"^\W+|\W+$", "", w) for w in chunk.lower().split()]
    chunk_words = [w for w in chunk_words if len(w) >= MIN_WORD_LENGTH]

    if not chunk_words:
        return 0

    best = 0

    for q_word in query_words:

        tolerance = max(1, int(len(q_word) * 0.3))
        candidates = [w for w in chunk_words if abs(len(w) - len(q_word)) <= tolerance]

        if not candidates:
            continue

        result = process.extractOne(q_word, candidates, scorer=fuzz.ratio, score_cutoff=FUZZY_WORD_THRESHOLD)

        if result is not None:
            best = max(best, result[1])

    return best


def search_documents(query, user_id, platform="all"):

    if not query:
        return []

    query_words = [w for w in query.lower().split() if len(w) >= MIN_WORD_LENGTH]

    hits = search_points("document", embed_text(query), user_id, platform, limit=QDRANT_LIMIT)

    scored = []

    for (_platform, _source_id), group in group_hits(hits).items():

        payload = group["payload"]
        chunks = group["chunks"]

        title_score = get_title_score(query, title_name(payload))
        content_score = get_content_score(query, " ".join(chunks))
        fuzzy_score = max((fuzzy_match_chunk(chunk, query_words) for chunk in chunks), default=0) / 100

        semantic_score = group["best"]
        if semantic_score < SEMANTIC_THRESHOLD:
            semantic_score = 0

        final_score = (
            0.40 * title_score +
            0.25 * content_score +
            0.10 * fuzzy_score +
            0.25 * semantic_score
        )

        if final_score < MIN_FINAL_SCORE:
            continue

        result = base_result(payload, "document", final_score)
        result.update({
            "title_score": title_score,
            "content_score": content_score,
            "fuzzy_score": fuzzy_score,
            "semantic_score": semantic_score,
            "preview": (chunks[0] if chunks else "")[:300],
        })
        scored.append(result)

    scored.sort(key=lambda r: r["score"], reverse=True)

    return scored[:TOP_K]
