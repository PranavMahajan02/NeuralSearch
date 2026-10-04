"""Every route must require a JWT unless it is explicitly public.

The routes are discovered from the OpenAPI schema, so new routes are covered
automatically. A second test makes sure no API route hides from the schema.
"""

import re

import pytest
from fastapi.routing import APIRoute


PUBLIC_ROUTES = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/"),
    ("GET", "/platforms/github/callback"),
}

# Interactive docs (development only) are not API routes.
DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def is_public(method: str, path: str) -> bool:

    if (method, path) in PUBLIC_ROUTES:
        return True

    return method == "GET" and path.endswith("/health")


def discovered_routes(app):

    routes = set()

    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            routes.add((method.upper(), path))

    return sorted(
        (method, path)
        for method, path in routes
        if path not in DOCS_PATHS
    )


def walk_api_routes(routes):

    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from walk_api_routes(nested.routes)


def test_no_api_route_is_hidden_from_the_schema(app):

    api_routes = list(walk_api_routes(app.routes))

    hidden = [
        route.path
        for route in api_routes
        if not route.include_in_schema
    ]

    assert len(api_routes) >= 30
    assert hidden == []


def concrete(path: str) -> str:

    return re.sub(r"\{[^}]+\}", "placeholder", path)


def test_route_discovery_finds_the_api(app):

    routes = discovered_routes(app)

    # Sanity check so the sweep below cannot pass vacuously.
    assert ("POST", "/search/") in routes
    assert ("POST", "/upload/") in routes
    assert ("DELETE", "/delete/{filename}") in routes
    assert ("GET", "/files/local") in routes
    assert len(routes) >= 30


def test_every_non_public_route_requires_auth(app, client):

    failures = []

    for method, path in discovered_routes(app):

        if is_public(method, path):
            continue

        response = client.request(method, concrete(path))

        if response.status_code != 401:
            failures.append(f"{method} {path} -> {response.status_code}")

    assert not failures, "Routes reachable without a token:\n" + "\n".join(failures)


@pytest.mark.parametrize("header", [
    "Bearer not-a-jwt",
    "Bearer ",
    "Basic dXNlcjpwYXNz",
])
def test_bad_credentials_are_rejected(client, header):

    response = client.post(
        "/search/",
        json={"query": "java"},
        headers={"Authorization": header}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_public_routes_answer_without_token(client):

    assert client.get("/").status_code == 200
    assert client.get("/search/health").status_code == 200
    assert client.get("/upload/health").status_code == 200


def test_old_unprefixed_upload_routes_are_gone(client):

    assert client.post("/").status_code in (404, 405)
    assert client.get("/health").status_code == 404
