"""Search entry point: one user-scoped query per requested modality."""

import logging
import time

from app.search.common import dedupe


logger = logging.getLogger("cogniseek.search")

PLATFORM_ALIASES = {"local_storage": "local"}


def _searchers():

    # Imported lazily: these modules import the embedding stack.
    from audio_search import search_audio
    from document_search_v2 import search_documents
    from image_search import search_images
    from video_search import search_video

    return {
        "document": search_documents,
        "image": search_images,
        "audio": search_audio,
        "video": search_video,
    }


def search(query: str, user_id, platform: str = "all", search_type: str = "all"):
    """Results for this user only: every Qdrant query below carries a
    must-filter on user_id (see app/vectorstore/query.py)."""

    if not user_id:
        raise ValueError("search() requires a user_id.")

    platform = PLATFORM_ALIASES.get(platform, platform)

    searchers = _searchers()

    if search_type == "all":
        selected = list(searchers.items())
    elif search_type in searchers:
        selected = [(search_type, searchers[search_type])]
    else:
        return []

    start = time.perf_counter()
    results = []

    for name, searcher in selected:
        t = time.perf_counter()
        results.extend(searcher(query, str(user_id), platform))
        logger.info("search %s: %.3f s", name, time.perf_counter() - t)

    logger.info("search total: %.3f s", time.perf_counter() - start)

    return dedupe(results)
