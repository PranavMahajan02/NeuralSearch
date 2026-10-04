import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_routes(app):

    added = []

    def boom():
        raise RuntimeError("secret internal detail")

    def teapot():
        raise HTTPException(status_code=418, detail="I am a teapot")

    for path, endpoint in (("/__test/boom", boom), ("/__test/teapot", teapot)):
        app.add_api_route(path, endpoint, methods=["GET"], include_in_schema=False)
        added.append(path)

    yield

    app.router.routes[:] = [
        route for route in app.router.routes
        if getattr(route, "path", None) not in added
    ]


def test_unhandled_exception_returns_generic_500(app, temp_routes, caplog):

    with TestClient(app, raise_server_exceptions=False) as raw_client:
        response = raw_client.get("/__test/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error.", "code": "internal_error"}
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text

    # The traceback is logged server-side.
    assert any("secret internal detail" in str(record.exc_info) for record in caplog.records if record.exc_info)


def test_http_exception_shape(client, temp_routes):

    response = client.get("/__test/teapot")

    assert response.status_code == 418
    assert response.json() == {"detail": "I am a teapot", "code": "error"}


def test_not_found_and_validation_shapes(client, user):

    missing = client.get("/no/such/route")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Not Found", "code": "not_found"}

    invalid = client.post("/search/", json={}, headers=user["headers"])
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    assert isinstance(invalid.json()["detail"], str)
    assert "query" in invalid.json()["detail"]


def test_security_headers(client):

    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_cors_allows_only_configured_origins(client):

    preflight = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type"
    }

    allowed = client.options("/search/", headers={"Origin": "http://localhost:3000", **preflight})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "PUT" not in allowed.headers["access-control-allow-methods"]

    denied = client.options("/search/", headers={"Origin": "http://evil.example", **preflight})
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers

    odd_header = client.options(
        "/search/",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "X-Custom"}
    )
    assert odd_header.status_code == 400


PRODUCTION_PROBE = """
import sys, types
from unittest.mock import MagicMock
stub = types.ModuleType("app.ai.model_manager"); stub.model_manager = MagicMock()
sys.modules["app.ai.model_manager"] = stub
from app.main import app
paths = app.openapi()["paths"]
print(app.openapi_url, app.docs_url, "/platforms/local/pick-folder" in paths)
"""


def test_production_disables_docs_and_folder_picker():

    env = dict(os.environ)
    env.update({"ENV": "production", "PYTHONPATH": str(ROOT)})

    result = subprocess.run(
        [sys.executable, "-c", PRODUCTION_PROBE],
        cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=180
    )

    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "None None False"


def test_development_exposes_docs_and_folder_picker(app):

    assert app.openapi_url == "/openapi.json"
    assert "/platforms/local/pick-folder" in app.openapi()["paths"]
