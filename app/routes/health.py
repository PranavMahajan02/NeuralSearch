"""Liveness and readiness.

/health: the process is up and serving (no dependencies checked) - a failing
liveness probe means "restart me".
/ready: every dependency answers - Postgres, Qdrant, Redis (when configured)
and the AI models (when preloaded). Used by compose healthchecks so Caddy only
starts once the API can actually serve. Details name the failing check, never
an error message (no hosts, users or keys).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings


router = APIRouter(tags=["Health"])


@router.get("/health")
def health():

    return {"status": "ok"}


def _database() -> bool:

    from app.database.db import engine

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def _qdrant() -> bool:

    from app.vectorstore.client import get_client

    get_client().get_collections()
    return True


def _redis() -> bool:

    if not settings.REDIS_URL:
        return True

    import redis

    client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
    try:
        return bool(client.ping())
    finally:
        client.close()


def _models() -> bool:

    from app.ai.model_manager import model_manager

    return model_manager.ready or not settings.PRELOAD_MODELS


CHECKS = {"database": _database, "qdrant": _qdrant, "redis": _redis, "models": _models}


@router.get("/ready")
def ready():

    results = {}
    for name, check in CHECKS.items():
        try:
            results[name] = bool(check())
        except Exception:
            results[name] = False

    ok = all(results.values())

    return JSONResponse({"status": "ready" if ok else "not_ready", "checks": results}, status_code=200 if ok else 503)
