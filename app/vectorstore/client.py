"""The process-wide Qdrant client (created lazily so tests can swap it)."""

import threading
from typing import Optional

from qdrant_client import QdrantClient

from app.core.config import settings


_client: Optional[QdrantClient] = None
_lock = threading.Lock()


def get_client() -> QdrantClient:

    global _client

    if _client is None:
        with _lock:
            if _client is None:
                if settings.QDRANT_LOCATION:
                    _client = QdrantClient(location=settings.QDRANT_LOCATION)
                else:
                    # https=False: Qdrant is only reachable on the internal network.
                    _client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY or None,
                        https=False,
                    )

    return _client


def set_client(client: Optional[QdrantClient]) -> None:
    """Tests only: install a client (e.g. QdrantClient(":memory:"))."""

    global _client
    _client = client
