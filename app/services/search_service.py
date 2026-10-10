"""Search: hybrid retrieval -> one ranking -> one global, paginated list."""

import logging
import os
import time

from app.core.clock import iso
from app.core.config import settings
from app.search.normalize import normalize_text, query_terms
from app.search.ranking import frame_z, possible_visual_matches, score_candidates
from app.search.retrieval import retrieve

logger = logging.getLogger("cogniseek.search")


def _display_path(candidate) -> str:
    """Never expose temporary download paths (BUG-23)."""

    path = candidate.path or ""

    def comparable(value: str) -> str:
        # Both separators on every OS: legacy rows written on Windows hold
        # "temp\name" and must be caught on a Linux server too.
        return value.replace("\\", "/").lower()

    temp_root = comparable(os.path.abspath(settings.TEMP_DIR)).rstrip("/") + "/"
    normalized = comparable(path)

    if normalized.startswith(temp_root) or normalized.startswith("temp/"):
        return candidate.file

    return path


EMPTY_METADATA = {"file_size": None, "modified_at": None, "mime_type": None}


def ledger_metadata(user_id, keys) -> dict:
    """{(platform, source_id): {file_size, modified_at (ISO), mime_type}} for one page."""

    from sqlalchemy import tuple_

    from app.database.db import SessionLocal
    from app.database.models import IndexedFile

    if not keys:
        return {}

    with SessionLocal() as db:
        rows = (
            db.query(
                IndexedFile.platform,
                IndexedFile.source_id,
                IndexedFile.size_bytes,
                IndexedFile.modified_at,
                IndexedFile.mime_type,
            )
            .filter(IndexedFile.user_id == user_id, tuple_(IndexedFile.platform, IndexedFile.source_id).in_(list(keys)))
            .all()
        )

    return {
        (platform, source_id): {
            "file_size": size,
            "modified_at": iso(modified),
            "mime_type": mime,
        }
        for platform, source_id, size, modified, mime in rows
    }


def suggestions(user_id, prefix: str, limit: int = 8) -> list:
    """File names of this user that start with / resemble `prefix` (pg_trgm)."""

    from sqlalchemy import text

    from app.database.db import SessionLocal

    prefix = normalize_text(prefix)

    if len(prefix) < 2:
        return []

    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT file_name, platform, file_type, starts, sim FROM (
                    SELECT DISTINCT ON (lower(file_name)) file_name, platform, file_type,
                           (lower(file_name) LIKE :starts ESCAPE '\\') AS starts,
                           word_similarity(:q, lower(file_name)) AS sim
                    FROM indexed_files
                    WHERE user_id = :user_id AND status = 'indexed'
                      AND (lower(file_name) LIKE :contains ESCAPE '\\' OR :q <% lower(file_name))
                    ORDER BY lower(file_name)
                ) matches
                ORDER BY starts DESC, sim DESC, length(file_name), file_name
                LIMIT :limit
            """),
            {"user_id": str(user_id), "q": prefix, "starts": f"{escaped}%", "contains": f"%{escaped}%", "limit": limit},
        ).fetchall()

    return [{"file": r.file_name, "platform": r.platform, "type": r.file_type} for r in rows]


def search(
    query: str,
    user_id,
    platform: str = "all",
    search_type: str = "all",
    limit: int = 20,
    offset: int = 0,
    debug: bool = False,
) -> dict:
    """Results for this user only: every Qdrant query carries a user_id
    must-filter (app/vectorstore/query.py) and the file-name query filters on
    user_id in SQL."""

    if not user_id:
        raise ValueError("search() requires a user_id.")

    start = time.perf_counter()

    normalized = normalize_text(query)

    # Nothing meaningful to look for (e.g. "!!!" or a single character).
    if len(normalized) < 2 or not query_terms(normalized):
        return {"total": 0, "results": [], "possible_matches": []}

    platform_filter = None if platform == "all" else platform

    candidates = retrieve(str(user_id), normalized, platform_filter, search_type)
    ranked = score_candidates(list(candidates.values()), normalized)

    page = ranked[offset : offset + limit]

    # Low-confidence visual tier: only for searches that can return images/videos,
    # only with the first page, never counted in total.
    possible = []
    if search_type in VISUAL_SEARCH_TYPES and offset == 0:
        possible = possible_visual_matches(list(candidates.values()), {item.candidate.key for item in ranked})

    metadata = ledger_metadata(user_id, [item.candidate.key for item in page + possible])

    results = [_result(item, metadata, debug) for item in page]
    possible_matches = [_result(item, metadata, debug) for item in possible]

    logger.info(
        "search: %d candidates -> %d results (%d returned, %d possible) in %.0f ms",
        len(candidates),
        len(ranked),
        len(results),
        len(possible_matches),
        (time.perf_counter() - start) * 1000,
    )

    return {"total": len(ranked), "results": results, "possible_matches": possible_matches}


VISUAL_SEARCH_TYPES = ("all", "image", "video")


def _result(item, metadata, debug) -> dict:
    """One API result (same shape for results and possible_matches)."""

    c = item.candidate
    path = _display_path(c)

    result = {
        "platform": c.platform,
        "source_id": c.source_id,
        "type": c.file_type,
        "file": c.file,
        "display_path": path,
        "path": path,
        "score": item.score,
        "match": item.match,
        **metadata.get(c.key, EMPTY_METADATA),
        "extension": os.path.splitext(c.file or "")[1].lower().lstrip(".") or None,
    }

    if c.platform == "github":
        result["owner"] = c.owner
        result["repo"] = c.repo

    if debug:
        result["debug"] = {
            "semantic": round(item.semantic, 4),
            "name": round(item.name, 4),
            "content": round(item.content, 4),
            "text_margin": c.text_margin,
            "clip_margin": c.clip_margin,
            "frame_z": frame_z(c),
            "text_cosine": c.text_cosine,
            "clip_cosine": c.clip_cosine,
            "name_similarity": c.name_similarity,
        }

    return result
