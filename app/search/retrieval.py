"""Candidate retrieval: vector search (Qdrant) + file-name search (pg_trgm).

Hybrid on purpose: vectors find files by meaning, the trigram index finds
files by (near-)matching names even when their content ranks low (BUG-21).
All queries for one request run concurrently, and each model embeds the
query once.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from app.database.db import SessionLocal
from app.search import calibration, query_vectors
from app.vectorstore.client import get_client
from app.vectorstore.config import collection_for_type
from app.vectorstore.query import user_filter


logger = logging.getLogger("cogniseek.search.retrieval")

# point type -> (vector space, Qdrant limit)
VECTOR_SOURCES = {
    "document": ("text", 200),
    "audio": ("text", 100),
    "video": ("text", 100),
    "image": ("clip", 60),
    "video_frame": ("clip", 300),
}

# search_type -> point types to query
TYPES_FOR_SEARCH = {
    "document": ("document",),
    "image": ("image",),
    "audio": ("audio",),
    "video": ("video", "video_frame"),
}

FILE_TYPE_OF_POINT = {"document": "document", "image": "image", "audio": "audio",
                      "video": "video", "video_frame": "video"}

TRIGRAM_LIMIT = 25
TRIGRAM_MIN_SIMILARITY = 0.45

_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="search")


@dataclass
class Chunk:

    text: str
    kind: str            # document | image | audio | video | video_frame
    score: float         # raw cosine


@dataclass
class Candidate:

    platform: str
    source_id: str
    file: str
    path: str
    file_type: str
    owner: Optional[str] = None
    repo: Optional[str] = None
    text_cosine: float = 0.0
    text_margin: Optional[float] = None
    clip_cosine: float = 0.0
    clip_margin: Optional[float] = None
    name_similarity: float = 0.0
    chunks: List[Chunk] = field(default_factory=list)

    @property
    def key(self) -> Tuple[str, str]:

        return self.platform, self.source_id


def search_types(search_type: str) -> List[str]:

    if search_type == "all":
        return list(VECTOR_SOURCES)

    return list(TYPES_FOR_SEARCH[search_type])


def _vector_query(point_type: str, vector, user_id: str, platform: Optional[str], limit: int):

    result = get_client().query_points(
        collection_name=collection_for_type(point_type),
        query=list(vector),
        query_filter=user_filter(user_id, platform),
        limit=limit,
        with_payload=True,
        with_vectors=True
    )

    return point_type, result.points


def _trigram_query(user_id: str, query: str, platform: Optional[str], file_types: List[str]):

    sql = """
        SELECT platform, source_id, file_name, display_path, file_type, owner, repo,
               GREATEST(similarity(file_name, :q), word_similarity(:q, file_name)) AS sim
        FROM indexed_files
        WHERE user_id = :user_id
          AND status = 'indexed'
          AND file_type = ANY(:types)
          AND (CAST(:platform AS text) IS NULL OR platform = CAST(:platform AS text))
          AND (file_name % :q OR :q <% file_name)
        ORDER BY sim DESC
        LIMIT :limit
    """

    with SessionLocal() as db:
        rows = db.execute(
            text(sql),
            {"user_id": user_id, "q": query, "platform": platform, "types": file_types, "limit": TRIGRAM_LIMIT}
        ).mappings().all()

    return [dict(row) for row in rows if row["sim"] >= TRIGRAM_MIN_SIMILARITY]


def retrieve(user_id: str, normalized_query: str, platform: Optional[str], search_type: str) -> Dict[Tuple[str, str], Candidate]:

    timings = {}
    start = time.perf_counter()

    point_types = search_types(search_type)
    spaces = {VECTOR_SOURCES[t][0] for t in point_types}

    # Each model embeds the query once (and the result is cached).
    vectors = {}
    if "text" in spaces:
        vectors["text"] = query_vectors.text_vector(normalized_query)
    if "clip" in spaces:
        vectors["clip"] = query_vectors.clip_vector(normalized_query)
    timings["embed"] = time.perf_counter() - start

    t = time.perf_counter()
    futures = [
        _pool.submit(_vector_query, point_type, vectors[VECTOR_SOURCES[point_type][0]],
                     user_id, platform, VECTOR_SOURCES[point_type][1])
        for point_type in point_types
    ]
    file_types = sorted({FILE_TYPE_OF_POINT[t] for t in point_types})
    trigram_future = _pool.submit(_trigram_query, user_id, normalized_query, platform, file_types)

    hits = [future.result() for future in futures]
    name_rows = trigram_future.result()
    timings["queries"] = time.perf_counter() - t

    candidates: Dict[Tuple[str, str], Candidate] = {}

    for point_type, points in hits:

        if not points:
            continue

        space = VECTOR_SOURCES[point_type][0]
        neutral = calibration.text_neutral_matrix() if space == "text" else calibration.clip_neutral_matrix()
        point_margins = calibration.margins([p.score for p in points], [p.vector for p in points], neutral)

        for point, margin in zip(points, point_margins):

            payload = point.payload or {}
            key = (payload.get("platform"), payload.get("source_id"))
            candidate = candidates.get(key)

            if candidate is None:
                candidate = candidates[key] = Candidate(
                    platform=payload.get("platform"),
                    source_id=payload.get("source_id"),
                    file=payload.get("file", ""),
                    path=payload.get("path", ""),
                    file_type=FILE_TYPE_OF_POINT[point_type],
                    owner=payload.get("owner"),
                    repo=payload.get("repo"),
                )

            score, margin = float(point.score), float(margin)

            if space == "text":
                candidate.text_cosine = max(candidate.text_cosine, score)
                candidate.text_margin = margin if candidate.text_margin is None else max(candidate.text_margin, margin)
            else:
                candidate.clip_cosine = max(candidate.clip_cosine, score)
                candidate.clip_margin = margin if candidate.clip_margin is None else max(candidate.clip_margin, margin)

            if point_type != "video_frame" and payload.get("chunk"):
                candidate.chunks.append(Chunk(text=payload["chunk"], kind=point_type, score=score))

    for row in name_rows:

        key = (row["platform"], row["source_id"])
        candidate = candidates.get(key)

        if candidate is None:
            candidate = candidates[key] = Candidate(
                platform=row["platform"], source_id=row["source_id"], file=row["file_name"],
                path=row["display_path"], file_type=row["file_type"], owner=row["owner"], repo=row["repo"],
            )

        candidate.name_similarity = max(candidate.name_similarity, float(row["sim"]))

    timings["total"] = time.perf_counter() - start

    logger.info(
        "retrieve: %d candidates (embed %.0f ms, queries %.0f ms, total %.0f ms)",
        len(candidates), timings["embed"] * 1000, timings["queries"] * 1000, timings["total"] * 1000
    )

    return candidates
