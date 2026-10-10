"""The process-wide Qdrant client (created lazily so tests can swap it).

Thread safety (the indexing pipeline calls it from several threads):
- server mode (production): qdrant-client talks HTTP through httpx.Client,
  which is documented as thread-safe (https://www.python-httpx.org/advanced/clients/);
- local mode (QDRANT_LOCATION=":memory:" or a path, used by the tests) is an
  in-process store that is NOT thread-safe, so its calls are serialized here.
"""

import threading
from typing import Optional

from qdrant_client import QdrantClient

from app.core.config import settings


_client: Optional[QdrantClient] = None
_lock = threading.Lock()


class _Serialized:
    """Proxy that runs every method of a local-mode client under one lock."""

    def __init__(self, client: QdrantClient):

        self._wrapped = client
        self._call_lock = threading.RLock()

    def __getattr__(self, name):

        attribute = getattr(self._wrapped, name)
        if not callable(attribute):
            return attribute

        def locked(*args, **kwargs):
            with self._call_lock:
                return attribute(*args, **kwargs)

        return locked


def _thread_safe(client):

    if client is None or isinstance(client, _Serialized):
        return client
    if type(getattr(client, "_client", None)).__name__ == "QdrantLocal":
        return _Serialized(client)
    return client


def get_client() -> QdrantClient:

    global _client

    if _client is None:
        with _lock:
            if _client is None:
                if settings.QDRANT_LOCATION:
                    _client = _thread_safe(QdrantClient(location=settings.QDRANT_LOCATION))
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
    _client = _thread_safe(client)
