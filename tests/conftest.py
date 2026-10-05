"""Test harness.

- Runs from a temporary working directory, so relative paths used by the app
  (index pickles, temp/) never touch the real project data. Every setting is
  pinned through environment variables.
- Uses a separate Postgres database (<db>_test) created through Alembic.
- Replaces the AI model manager with a stub so no model is ever loaded
  (set COGNISEEK_TEST_REAL_MODELS=1 to use the real one).
"""

import os
import secrets
import sys
import tempfile
import types
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Environment (must be set before anything imports app.core.config)
# ---------------------------------------------------------------------------

_dotenv = dotenv_values(ROOT / ".env")

_base_url = os.environ.get("DATABASE_URL") or _dotenv.get("DATABASE_URL")

if not _base_url:
    raise RuntimeError("DATABASE_URL must be set (in .env or the environment) to run tests.")

_server_url, _db_name = _base_url.rsplit("/", 1)

TEST_DB_NAME = _db_name.split("?")[0] + "_test"
TEST_DATABASE_URL = f"{_server_url}/{TEST_DB_NAME}"

WORK_DIR = Path(tempfile.mkdtemp(prefix="cogniseek-tests-"))
DATA_DIR = WORK_DIR / "data"
LOCAL_ROOT = WORK_DIR / "local-root"

DATA_DIR.mkdir()
LOCAL_ROOT.mkdir()

os.environ.update({
    "ENV": "development",
    "DATABASE_URL": TEST_DATABASE_URL,
    "JWT_SECRET_KEY": secrets.token_urlsafe(48),
    "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "DATA_DIR": str(DATA_DIR),
    "ALLOWED_LOCAL_ROOTS": str(LOCAL_ROOT),
    "AUTH_RATE_LIMIT": "5/minute",
    "MAX_UPLOAD_MB": "1",
    "CORS_ORIGINS": "http://localhost:3000",
    "FRONTEND_URL": "http://localhost:3000",
    "COGNISEEK_SKIP_MODEL_PRELOAD": "1",
    # Tests drive the indexing worker explicitly (IndexingWorker.run_once).
    "COGNISEEK_DISABLE_WORKER": "1",
    # In-process Qdrant + a throwaway prefix: tests can never reach the real
    # collections (cogniseek_v2_* / cogniseek*).
    "QDRANT_LOCATION": ":memory:",
    "QDRANT_COLLECTION_PREFIX": f"test_{uuid.uuid4().hex[:12]}",
    "TEMP_DIR": str(WORK_DIR / "temp"),
    "BACKEND_PUBLIC_URL": "http://127.0.0.1:8000",
    "GITHUB_OAUTH_CONFIG_PATH": str(WORK_DIR / "no-github-oauth.json"),
    "GOOGLE_CLIENT_SECRET_PATH": str(WORK_DIR / "no-client-secret.json"),
})


assert os.environ["QDRANT_COLLECTION_PREFIX"].startswith("test_")


if os.environ.get("COGNISEEK_TEST_REAL_MODELS") != "1":

    stub = types.ModuleType("app.ai.model_manager")
    stub.model_manager = MagicMock(name="model_manager")
    stub.ModelManager = MagicMock(name="ModelManager")
    sys.modules["app.ai.model_manager"] = stub


# ---------------------------------------------------------------------------
# Test database
# ---------------------------------------------------------------------------

def _create_test_database():

    admin = create_engine(
        f"{_server_url}/postgres",
        isolation_level="AUTOCOMMIT"
    )

    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))

    admin.dispose()

    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    config.attributes["configure_logger"] = False

    command.upgrade(config, "head")


_create_test_database()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _isolated_working_dir():
    """Run every test from WORK_DIR so relative paths (pickles, temp/) can never
    reach the real project data. Done in a fixture, not at import time, so
    pytest resolves `testpaths` from the project root first."""

    previous = os.getcwd()
    os.chdir(WORK_DIR)

    yield

    os.chdir(previous)


@pytest.fixture(scope="session")
def app():

    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def client(app):

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limiter():

    from app.core.rate_limit import limiter

    limiter.reset()

    yield


@pytest.fixture
def db():

    from app.database.db import SessionLocal

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def local_root():

    return LOCAL_ROOT


@pytest.fixture
def make_user(client):
    """Register + log in a fresh user. Returns dict(id, email, password, token, headers)."""

    from app.core.rate_limit import limiter

    def _make(password="Password123"):

        email = f"user-{uuid.uuid4().hex[:10]}@example.com"

        registered = client.post(
            "/auth/register",
            json={"name": "Test User", "email": email, "password": password}
        )
        assert registered.status_code == 200, registered.text

        login = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        assert login.status_code == 200, login.text

        # Fixture logins must not count against rate-limit tests.
        limiter.reset()

        token = login.json()["access_token"]

        return {
            "id": registered.json()["id"],
            "email": email,
            "password": password,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"}
        }

    return _make


@pytest.fixture
def user(make_user):

    return make_user()


# ---------------------------------------------------------------------------
# Deterministic fake embeddings (no models)
# ---------------------------------------------------------------------------

import hashlib
import math
import re as _re


def _bag_of_words_vector(text: str, size: int):
    """Hashed bag of words, L2-normalized: cosine similarity tracks word overlap."""

    vector = [0.0] * size

    for word in _re.findall(r"\w+", (text or "").lower()):
        bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % size
        vector[bucket] += 1.0

    norm = math.sqrt(sum(v * v for v in vector))

    if norm == 0:
        vector[0] = 1.0
        return vector

    return [v / norm for v in vector]


class FakeEmbedder:

    def text(self, texts):
        return [_bag_of_words_vector(t, 384) for t in texts]

    def clip_text(self, text):
        return _bag_of_words_vector(text, 512)

    def clip_image(self, path):
        # Test images are text files: their content stands in for pixels.
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return _bag_of_words_vector(f.read(), 512)


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):

    import app.ai.embedder as embedder

    monkeypatch.setattr(embedder, "backend", FakeEmbedder())

    yield


@pytest.fixture(scope="session", autouse=True)
def _assert_test_qdrant():

    from app.core.config import settings
    from app.vectorstore.client import get_client

    assert settings.QDRANT_LOCATION == ":memory:"
    assert settings.QDRANT_COLLECTION_PREFIX.startswith("test_")
    assert get_client()._client.__class__.__name__ == "QdrantLocal"

    yield
