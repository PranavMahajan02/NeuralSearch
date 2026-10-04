import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Root modules (document_search_v2, clip_utils, ...) are imported by app/ as top-level modules.
sys.path.insert(0, str(ROOT))

# Run from the project root so relative paths (.env, *.pkl, credentials/) resolve.
os.chdir(ROOT)

# Skip the duplicate eager model preload in the startup hook.
os.environ.setdefault("COGNISEEK_SKIP_MODEL_PRELOAD", "1")


@pytest.fixture(scope="session")
def app():

    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def client(app):

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
