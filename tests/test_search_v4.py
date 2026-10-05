"""Phase 4: validation, normalization, hybrid retrieval, ranking, caching, model loading."""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint
from app.services.indexing_pipeline import index_local_file
from tests.conftest import _bag_of_words_vector


ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def folder(local_root):

    path = local_root / f"s4-{uuid.uuid4().hex[:8]}"
    path.mkdir()
    return path


def write(path: Path, text: str) -> Path:

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def post(client, user, body, debug=False):

    url = "/search/?debug=true" if debug else "/search/"
    return client.post(url, json=body, headers=user["headers"])


def results(client, user, query, debug=False, **params):

    response = post(client, user, {"query": query, **params}, debug=debug)
    assert response.status_code == 200, response.text
    return response.json()


def add_point(user, platform, source_id, file_name, file_type, point_type, text, display_path=None, chunk_index=0):

    size = 384 if point_type in ("document", "audio", "video") else 512
    meta = FileMeta(user_id=user["id"], platform=platform, source_id=source_id, file_name=file_name,
                    display_path=display_path or file_name, file_type=file_type, version="v1")
    vector = _bag_of_words_vector(text, size)
    index_store.upsert_file(meta, [IndexPoint(point_type, vector, chunk_index, text)])


# ---------------------------------------------------------------------------
# Validation (BUG-22)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body, fragment", [
    ({"query": ""}, "empty"),
    ({"query": "   \t "}, "empty"),
    ({"query": "x" * 501}, "500"),
    ({"query": "java", "platform": "dropbox"}, "platform"),
    ({"query": "java", "search_type": "spreadsheet"}, "search_type"),
    ({"query": "java", "limit": 0}, "limit"),
    ({"query": "java", "limit": 51}, "limit"),
    ({"query": "java", "offset": -1}, "offset"),
    ({}, "query"),
])
def test_invalid_requests_are_422(client, user, body, fragment):

    response = post(client, user, body)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert fragment in response.json()["detail"].lower()


def test_aliases_and_case_insensitive_values(client, user):

    body = results(client, user, "java", platform="local_storage", search_type="Document")

    assert body["platform"] == "local"
    assert body["search_type"] == "document"
    assert (body["limit"], body["offset"], body["total"]) == (20, 0, 0)


def test_query_is_stripped_and_punctuation_only_returns_nothing(client, user):

    assert results(client, user, "  java  ")["query"] == "java"
    assert results(client, user, "!!!")["results"] == []
    assert results(client, user, "a")["results"] == []


def test_max_length_query_is_accepted(client, user):

    assert post(client, user, {"query": "word " * 100}).status_code == 200


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_text():

    from app.search.normalize import normalize_name, normalize_text, query_terms

    assert normalize_text("  JAVA!!!@#$% ") == "java"
    assert normalize_text("Ｊａｖａ   Notes") == "java notes"          # NFKC + whitespace
    assert normalize_name("Hospital_Management-System (2).pptx") == "hospital management system 2"
    assert query_terms("how should a project report be formatted") == ["project", "report", "formatted"]
    assert query_terms("the") == ["the"]


def test_punctuated_and_upper_case_queries_match_like_plain(client, user, folder):

    write(folder / "Java Basics.txt", "classes objects inheritance")
    client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=user["headers"])
    index_local_file(user["id"], str(folder / "Java Basics.txt"))

    plain = [r["source_id"] for r in results(client, user, "java")["results"]]
    for variant in ("JAVA", "java!!!@#$%", "  Java  "):
        assert [r["source_id"] for r in results(client, user, variant)["results"]] == plain
    assert len(plain) == 1


@pytest.mark.parametrize("term, word, expected", [
    ("java", "java", 1.0),
    ("jva", "java", 0.85),            # typo
    ("format", "formatted", 0.9),     # prefix
    ("2024", "2025", 0.0),            # numbers must match exactly
    ("cat", "cart", 0.85),
    ("tax", "taxes", 0.0),
])
def test_term_match(term, word, expected):

    from app.search.ranking import term_match

    assert term_match(term, word) == expected


# ---------------------------------------------------------------------------
# Hybrid retrieval: file-name rescue (BUG-21)
# ---------------------------------------------------------------------------

def test_exact_file_name_is_found_even_when_its_chunks_rank_low(client, user, folder, monkeypatch):

    import app.search.retrieval as retrieval

    # Vector search only returns the single best chunk...
    monkeypatch.setitem(retrieval.VECTOR_SOURCES, "document", ("text", 1))

    write(folder / "turing machine notes.txt", "lorem ipsum dolor sit amet")
    write(folder / "automata.txt", "a turing machine reads a tape; turing machine states")
    client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=user["headers"])
    for name in ("turing machine notes.txt", "automata.txt"):
        index_local_file(user["id"], str(folder / name))

    found = results(client, user, "turing machine notes", debug=True)["results"]

    # ...but the trigram file-name lookup brings the exact name back, ranked first.
    assert found[0]["file"] == "turing machine notes.txt"
    assert "filename" in found[0]["match"]["reasons"]
    assert found[0]["debug"]["name_similarity"] >= 0.9


def test_file_name_lookup_is_scoped_to_the_user(client, make_user, folder):

    owner, other = make_user(), make_user()

    write(folder / "quarterly budget plan.txt", "numbers")
    client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=owner["headers"])
    index_local_file(owner["id"], str(folder / "quarterly budget plan.txt"))

    assert len(results(client, owner, "quarterly budget plan")["results"]) == 1
    assert results(client, other, "quarterly budget plan")["results"] == []


# ---------------------------------------------------------------------------
# Global ranking, merge, pagination, dedupe
# ---------------------------------------------------------------------------

def test_modalities_are_merged_into_one_sorted_page(client, user):

    add_point(user, "google_drive", "D1", "volcano report.docx", "document", "document", "volcano eruption lava report")
    add_point(user, "google_drive", "A1", "volcano talk.mp3", "audio", "audio", "a talk about a volcano eruption")
    add_point(user, "google_drive", "V1", "volcano film.mp4", "video", "video", "volcano eruption footage narration")
    add_point(user, "google_drive", "D2", "volcano notes.txt", "document", "document", "volcano")
    add_point(user, "google_drive", "D3", "cooking.txt", "document", "document", "pasta recipe")

    full = results(client, user, "volcano eruption")
    items = full["results"]

    assert {r["type"] for r in items} == {"document", "audio", "video"}
    assert [r["score"] for r in items] == sorted((r["score"] for r in items), reverse=True)
    assert all(0 <= r["score"] <= 1 for r in items)
    assert len({(r["platform"], r["source_id"]) for r in items}) == len(items)
    assert "cooking.txt" not in [r["file"] for r in items]
    assert full["total"] == len(items) == 4

    page = results(client, user, "volcano eruption", limit=2, offset=1)
    assert page["total"] == 4
    assert [r["source_id"] for r in page["results"]] == [r["source_id"] for r in items[1:3]]

    assert results(client, user, "volcano eruption", offset=10)["results"] == []


def test_search_type_limits_modalities(client, user):

    add_point(user, "google_drive", "D1", "volcano report.docx", "document", "document", "volcano eruption")
    add_point(user, "google_drive", "A1", "volcano talk.mp3", "audio", "audio", "volcano eruption")

    assert {r["type"] for r in results(client, user, "volcano eruption", search_type="audio")["results"]} == {"audio"}


def test_negative_query_returns_nothing(client, user):

    add_point(user, "google_drive", "D1", "report.docx", "document", "document", "annual sales report figures")
    add_point(user, "google_drive", "I1", "beach.jpg", "image", "image", "sunny beach with palm trees")

    # The fake embedder makes vectors of unrelated words orthogonal.
    assert results(client, user, "xqzv wplk qqq")["results"] == []
    assert results(client, user, "zzzzzz")["total"] == 0


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

def test_result_shape_match_object_and_no_debug_fields(client, user):

    add_point(user, "google_drive", "D1", "volcano report.docx", "document", "document",
              "The volcano eruption in 2024 covered the village in ash for three days.")

    result = results(client, user, "volcano eruption")["results"][0]

    assert set(result) == {"platform", "source_id", "type", "file", "display_path", "path", "score", "match"}
    match = result["match"]
    assert set(match) == {"reasons", "field", "snippet", "highlights"}
    assert "filename" in match["reasons"] and "content" in match["reasons"]
    assert len(match["snippet"]) <= 200
    marked = [match["snippet"][start:end].lower() for start, end in match["highlights"]]
    assert set(marked) == {"volcano", "eruption"}


def test_debug_fields_only_on_request_and_never_in_production(client, user, monkeypatch):

    add_point(user, "google_drive", "D1", "volcano.docx", "document", "document", "volcano")

    assert "debug" in results(client, user, "volcano", debug=True)["results"][0]

    from app.core.config import settings
    monkeypatch.setattr(settings, "ENV", "production")

    response = post(client, user, {"query": "volcano"}, debug=True)
    assert response.status_code == 400


def test_temporary_paths_are_never_returned(client, user):

    from app.core.config import settings

    temp_path = os.path.join(settings.TEMP_DIR, "jobs", "abc", "000001", "volcano.docx")
    add_point(user, "google_drive", "D1", "volcano.docx", "document", "document", "volcano", display_path=temp_path)
    add_point(user, "google_drive", "D2", "volcano 2.docx", "document", "document", "volcano", display_path="temp\\volcano 2.docx")

    for result in results(client, user, "volcano")["results"]:
        assert not result["path"].lower().startswith(os.path.abspath(settings.TEMP_DIR).lower())
        assert not result["path"].lower().startswith("temp")
        assert result["path"] == result["display_path"] == result["file"]


def test_github_results_carry_owner_and_repo(client, user):

    add_point(user, "github", "octo/app:src/volcano.py", "volcano.py", "document", "document", "def volcano(): pass",
              display_path="octo/app/src/volcano.py")
    from app.services.index_store import get_source
    # GitHub rows need owner/repo in the ledger; add_point used none, so set via FileMeta.
    meta = FileMeta(user_id=user["id"], platform="github", source_id="octo/app:src/volcano.py", file_name="volcano.py",
                    display_path="octo/app/src/volcano.py", file_type="document", version="sha", owner="octo", repo="app")
    index_store.upsert_file(meta, [IndexPoint("document", _bag_of_words_vector("def volcano(): pass", 384), 0, "def volcano(): pass")])

    result = results(client, user, "volcano")["results"][0]

    assert (result["owner"], result["repo"], result["display_path"]) == ("octo", "app", "octo/app/src/volcano.py")
    assert get_source(user["id"], "github", "octo/app:src/volcano.py").repo == "app"


# ---------------------------------------------------------------------------
# Caching, CLIP truncation, model loading
# ---------------------------------------------------------------------------

def test_query_embeddings_are_cached(client, user):

    import app.ai.embedder as embedder

    calls = {"text": 0, "clip": 0}
    real = embedder.backend

    class Counting:
        def text(self, texts):
            calls["text"] += 1
            return real.text(texts)

        def clip_text(self, text):
            calls["clip"] += 1
            return real.clip_text(text)

        def clip_image(self, path):
            return real.clip_image(path)

    embedder.backend = Counting()
    from app.search import calibration
    calibration.text_neutral_matrix()   # computed once, not counted below
    calibration.clip_neutral_matrix()
    calls.update(text=0, clip=0)

    results(client, user, "Volcano Eruption")
    results(client, user, "volcano   eruption!!")   # same normalized query
    results(client, user, "volcano eruption", search_type="image")

    # One MiniLM and one CLIP encoding in total.
    assert calls == {"text": 1, "clip": 1}


def test_clip_text_encoding_truncates_to_77_tokens(monkeypatch):

    import numpy as np
    import torch
    from unittest.mock import MagicMock

    from app.ai import encoders

    captured = {}

    def processor(**kwargs):
        captured.update(kwargs)
        return {"input_ids": torch.zeros((1, 77), dtype=torch.long)}

    model = MagicMock()
    model.get_text_features.return_value = torch.ones((1, 512))

    manager = MagicMock()
    manager.clip_processor = processor
    manager.clip_model = model
    manager.device = "cpu"
    manager.clip_lock = __import__("threading").Lock()
    monkeypatch.setattr(encoders, "model_manager", manager)

    vector = encoders.encode_clip_text("word " * 2000)

    assert captured["truncation"] is True
    assert captured["max_length"] == 77
    assert len(vector) == 512 and np.allclose(vector, 1.0)


IMPORT_PROBE = r"""
import sys, types

class Boom:
    def __init__(self, *a, **k):
        raise RuntimeError("model constructed at import time")
    from_pretrained = classmethod(lambda cls, *a, **k: cls())

# Any attempt to construct a model while importing the app fails loudly.
for name, attrs in {
    "sentence_transformers": ["SentenceTransformer"],
    "faster_whisper": ["WhisperModel"],
    "paddleocr": ["PaddleOCR"],
}.items():
    module = types.ModuleType(name)
    for attr in attrs:
        setattr(module, attr, Boom)
    sys.modules[name] = module

import app.main  # noqa

heavy = [m for m in ("torch", "transformers", "cv2", "moviepy", "paddle") if m in sys.modules]
print("HEAVY:", ",".join(heavy) or "none")
"""


def test_importing_the_app_loads_no_model():

    env = dict(os.environ, PYTHONPATH=str(ROOT))

    result = subprocess.run(
        [sys.executable, "-c", IMPORT_PROBE],
        cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=300
    )

    assert result.returncode == 0, result.stderr[-3000:]
    assert result.stdout.strip().splitlines()[-1] == "HEAVY: none"


def test_model_manager_loads_lazily_and_once(monkeypatch):

    import importlib.util
    import types

    created = []

    class FakeST:
        def __init__(self, *args, **kwargs):
            created.append(args)

    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = FakeST
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    # conftest stubs app.ai.model_manager; load the real file directly.
    spec = importlib.util.spec_from_file_location("real_model_manager", ROOT / "app" / "ai" / "model_manager.py")
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)

    manager = real.ModelManager()
    manager._device = "cpu"

    assert created == []
    first = manager.semantic_model
    second = manager.semantic_model
    assert first is second and len(created) == 1
