"""Phase 7A-C4: rate limits - per user on /search and OAuth connect, shared storage."""

import pytest
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import settings


def _request(headers=None, host="203.0.113.7"):

    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "client": (host, 1234), "path": "/", "method": "GET"})


def test_user_key_uses_the_verified_user_and_falls_back_to_the_ip(user):

    assert rate_limit.user_key(_request({"Authorization": f"Bearer {user['token']}"})) == f"user:{user['id']}"
    assert rate_limit.user_key(_request({"Authorization": "Bearer forged.token.value"})) == "ip:203.0.113.7"
    assert rate_limit.user_key(_request()) == "ip:203.0.113.7"


def test_search_is_limited_per_user(client, make_user, monkeypatch):

    import app.routes.search as search_route

    monkeypatch.setattr(search_route, "search", lambda **_: {"total": 0, "results": [], "possible_matches": []})
    limit = int(settings.SEARCH_RATE_LIMIT.split("/")[0])
    first, second = make_user(), make_user()

    statuses = [
        client.post("/search/", json={"query": "q"}, headers=first["headers"]).status_code for _ in range(limit + 1)
    ]
    assert statuses[:limit] == [200] * limit and statuses[-1] == 429

    # Another user (same client IP) has their own bucket.
    assert client.post("/search/", json={"query": "q"}, headers=second["headers"]).status_code == 200


@pytest.mark.parametrize("path", ["/platforms/google-drive/connect", "/platforms/github/connect"])
def test_oauth_connect_is_limited(client, user, path, monkeypatch):

    import app.routes.github as github_route

    monkeypatch.setattr(github_route, "get_authorization_url", lambda state: "https://github.example/o")
    limit = int(settings.OAUTH_RATE_LIMIT.split("/")[0])

    statuses = [client.get(path, headers=user["headers"]).status_code for _ in range(limit + 1)]

    assert statuses[-1] == 429
    assert 429 not in statuses[:limit]
    assert github_route.limiter is rate_limit.limiter


def test_storage_is_redis_when_configured():

    # Development/tests: in-memory; production (REDIS_URL required) uses Redis.
    expected = settings.REDIS_URL or "memory://"
    assert rate_limit.limiter._storage_uri == expected
