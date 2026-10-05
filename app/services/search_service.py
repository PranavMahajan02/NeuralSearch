"""Search: hybrid retrieval -> one ranking -> one global, paginated list."""

import logging
import os
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.search.normalize import normalize_text, query_terms
from app.search.ranking import score_candidates
from app.search.retrieval import retrieve


logger = logging.getLogger("cogniseek.search")


def _display_path(candidate) -> str:
    """Never expose temporary download paths (BUG-23)."""

    path = candidate.path or ""
    temp_root = os.path.normcase(os.path.abspath(settings.TEMP_DIR))
    normalized = os.path.normcase(path)

    if (
        normalized.startswith(temp_root)
        or normalized.startswith(os.path.normcase("temp" + os.sep))
        or normalized.startswith("temp/")
    ):
        return candidate.file

    return path


def search(
    query: str,
    user_id,
    platform: str = "all",
    search_type: str = "all",
    limit: int = 20,
    offset: int = 0,
    debug: bool = False
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
        return {"total": 0, "results": []}

    platform_filter = None if platform == "all" else platform

    candidates = retrieve(str(user_id), normalized, platform_filter, search_type)
    ranked = score_candidates(list(candidates.values()), normalized)

    page = ranked[offset:offset + limit]

    results = []

    for item in page:

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
                "text_cosine": c.text_cosine,
                "clip_cosine": c.clip_cosine,
                "name_similarity": c.name_similarity,
            }

        results.append(result)

    logger.info(
        "search: %d candidates -> %d results (%d returned) in %.0f ms",
        len(candidates), len(ranked), len(results), (time.perf_counter() - start) * 1000
    )

    return {"total": len(ranked), "results": results}
