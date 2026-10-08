"""Shared slowapi limiter.

Counters live in Redis (settings.REDIS_URL) so they are shared by every worker
and survive restarts; development without Redis uses in-memory counters. If
Redis becomes unreachable the limiter falls back to memory instead of failing
requests.

Keys: per client IP (login/register: there is no user yet), or per user for
authenticated endpoints (user_key), so users behind one NAT do not share a bucket.
The client IP is the real one: uvicorn runs with --proxy-headers behind Caddy.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def user_key(request: Request) -> str:
    """'user:<id>' for a valid bearer token, else 'ip:<address>'. The token is
    verified (cheap HMAC), so a forged one cannot pick someone else's bucket."""

    from app.auth.jwt_handler import verify_token

    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        payload = verify_token(header[7:].strip())
        subject = payload and (payload.get("user_id") or payload.get("sub"))
        if subject:
            return f"user:{subject}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL or "memory://",
    in_memory_fallback_enabled=bool(settings.REDIS_URL),
    key_prefix="cogniseek",
)
