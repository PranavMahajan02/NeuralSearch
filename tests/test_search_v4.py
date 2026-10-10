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
    meta = FileMeta(
        user_id=user["id"],
        platform=platform,
        source_id=source_id,
        file_name=file_name,
        display_path=display_path or file_name,
        file_type=file_type,
        version="v1",
    )
    vector = _bag_of_words_vector(text, size)
    index_store.upsert_file(meta, [IndexPoint(point_type, vector, chunk_index, text)])


# ---------------------------------------------------------------------------
# Validation (BUG-22)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, fragment",
    [
        ({"query": ""}, "empty"),
        ({"query": "   \t "}, "empty"),
        ({"query": "x" * 501}, "500"),
        ({"query": "java", "platform": "dropbox"}, "platform"),
        ({"query": "java", "search_type": "spreadsheet"}, "search_type"),
        ({"query": "java", "limit": 0}, "limit"),
        ({"query": "java", "limit": 51}, "limit"),
        ({"query": "java", "offset": -1}, "offset"),
        ({}, "query"),
    ],
)
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
    assert normalize_text("Ｊａｖａ   Notes") == "java notes"  # NFKC + whitespace
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


@pytest.mark.parametrize(
    "term, word, expected",
    [
        ("java", "java", 1.0),
        ("jva", "java", 0.85),  # typo
        ("format", "formatted", 0.9),  # prefix
        ("2024", "2025", 0.0),  # numbers must match exactly
        ("cat", "cart", 0.85),
        ("tax", "taxes", 0.0),
    ],
)
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

    add_point(
        user,
        "google_drive",
        "D1",
        "volcano report.docx",
        "document",
        "document",
        "The volcano eruption in 2024 covered the village in ash for three days.",
    )

    result = results(client, user, "volcano eruption")["results"][0]

    assert set(result) == {
        "platform",
        "source_id",
        "type",
        "file",
        "display_path",
        "path",
        "score",
        "match",
        "file_size",
        "modified_at",
        "mime_type",
        "extension",
    }
    # Not indexed through a connector here: metadata is unknown (null), the extension is derived.
    assert (result["file_size"], result["modified_at"], result["extension"]) == (None, None, "docx")
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
    add_point(
        user,
        "google_drive",
        "D2",
        "volcano 2.docx",
        "document",
        "document",
        "volcano",
        display_path="temp\\volcano 2.docx",
    )

    for result in results(client, user, "volcano")["results"]:
        assert not result["path"].lower().startswith(os.path.abspath(settings.TEMP_DIR).lower())
        assert not result["path"].lower().startswith("temp")
        assert result["path"] == result["display_path"] == result["file"]


def test_github_results_carry_owner_and_repo(client, user):

    add_point(
        user,
        "github",
        "octo/app:src/volcano.py",
        "volcano.py",
        "document",
        "document",
        "def volcano(): pass",
        display_path="octo/app/src/volcano.py",
    )
    from app.services.index_store import get_source

    # GitHub rows need owner/repo in the ledger; add_point used none, so set via FileMeta.
    meta = FileMeta(
        user_id=user["id"],
        platform="github",
        source_id="octo/app:src/volcano.py",
        file_name="volcano.py",
        display_path="octo/app/src/volcano.py",
        file_type="document",
        version="sha",
        owner="octo",
        repo="app",
    )
    index_store.upsert_file(
        meta, [IndexPoint("document", _bag_of_words_vector("def volcano(): pass", 384), 0, "def volcano(): pass")]
    )

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

    calibration.text_neutral_matrix()  # computed once, not counted below
    calibration.clip_neutral_matrix()
    calls.update(text=0, clip=0)

    results(client, user, "Volcano Eruption")
    results(client, user, "volcano   eruption!!")  # same normalized query
    results(client, user, "volcano eruption", search_type="image")

    # One MiniLM and one CLIP encoding in total.
    assert calls == {"text": 1, "clip": 1}


def test_clip_text_encoding_truncates_to_77_tokens(monkeypatch):

    from unittest.mock import MagicMock

    import numpy as np
    import torch

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
        [sys.executable, "-c", IMPORT_PROBE], cwd=os.getcwd(), env=env, capture_output=True, text=True, timeout=300
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


# ---------------------------------------------------------------------------
# Phase 5 bug #3: pure visual image search
# ---------------------------------------------------------------------------


def image(file, margin, ocr="", platform="local", source_id=None):

    from app.search.retrieval import Candidate, Chunk

    candidate = Candidate(
        platform=platform, source_id=source_id or file, file=file, path=file, file_type="image", clip_margin=margin
    )
    candidate.chunks.append(Chunk(text=ocr, kind="image", score=0.2))

    return candidate


def test_a_strong_clip_margin_alone_returns_an_image_without_name_match():

    from app.search.ranking import IMAGE_MARGIN_EVIDENCE, score_candidates

    scored = score_candidates([image("IMG_0042.webp", IMAGE_MARGIN_EVIDENCE + 0.02)], "dog")

    assert [s.candidate.file for s in scored] == ["IMG_0042.webp"]
    assert scored[0].name == 0 and scored[0].reasons == ["visual"]


def test_a_weak_clip_margin_alone_is_not_evidence():

    from app.search.ranking import IMAGE_MARGIN_EVIDENCE, score_candidates

    assert score_candidates([image("IMG_0042.webp", IMAGE_MARGIN_EVIDENCE - 0.01)], "dog") == []


def test_photos_of_documents_need_text_or_name_evidence():

    from app.search.ranking import score_candidates

    page = " ".join(["candidate roll number examination centre subject"] * 5)

    assert score_candidates([image("WhatsApp Image.jpeg", 0.07, ocr=page)], "tax return form") == []


@pytest.mark.parametrize("query", ["a photo of a dog", "show me the image of my dog", "find dog pictures"])
def test_generic_words_never_match_on_their_own(query):

    from app.search.normalize import query_terms
    from app.search.ranking import score_candidates

    assert query_terms(query) == ["dog"]

    scored = score_candidates(
        [
            image("Golden_Retriever.webp", 0.06),  # the dog, no query word in its name
            image("photo of the image file.jpg", -0.02),  # only generic words in common
            image("my pictures.png", -0.03),
        ],
        query,
    )

    assert [s.candidate.file for s in scored] == ["Golden_Retriever.webp"]


def test_repository_folders_count_as_name_words():

    from app.search.ranking import score_candidates
    from app.search.retrieval import Candidate

    manifest = Candidate(
        platform="github",
        source_id="me/tool:extension/manifest.json",
        file="manifest.json",
        path="me/tool/extension/manifest.json",
        file_type="document",
    )

    scored = score_candidates([manifest], "chrome extension manifest")

    assert [s.candidate.file for s in scored] == ["manifest.json"] and "filename" in scored[0].reasons


@pytest.mark.parametrize("file, returned", [("notes.pdf", True), ("chart.tsx", False), ("deploy.yaml", False)])
def test_code_files_need_a_higher_semantic_margin(file, returned):

    from app.search.ranking import TEXT_MARGIN_EVIDENCE, TEXT_MARGIN_EVIDENCE_CODE, score_candidates
    from app.search.retrieval import Candidate

    margin = (TEXT_MARGIN_EVIDENCE + TEXT_MARGIN_EVIDENCE_CODE) / 2
    candidate = Candidate(
        platform="github", source_id=f"me/r:{file}", file=file, path=file, file_type="document", text_margin=margin
    )

    assert bool(score_candidates([candidate], "kubernetes helm deployment")) is returned


# ---------------------------------------------------------------------------
# Phase 6: result metadata, suggestions, recent files, job history
# ---------------------------------------------------------------------------


def test_local_results_carry_size_modified_time_and_mime(client, user, folder):

    path = write(folder / "volcano notes.txt", "volcano eruption ash cloud")
    index_local_file(user["id"], str(path))

    result = results(client, user, "volcano notes")["results"][0]

    assert result["file_size"] == path.stat().st_size
    assert result["modified_at"].endswith("+00:00") and result["modified_at"][:4].isdigit()
    assert (result["mime_type"], result["extension"]) == ("text/plain", "txt")


def test_suggestions_are_prefix_first_and_scoped_to_the_user(client, user, make_user):

    other = make_user()
    for name in ("Quantum notes.pdf", "quantum physics.docx", "notes quantum.txt", "Turing.pdf"):
        add_point(user, "google_drive", f"S-{name}", name, "document", "document", "text")
    add_point(other, "google_drive", "S-x", "quantum secret.pdf", "document", "document", "text")

    response = client.get("/search/suggestions", params={"prefix": "quan"}, headers=user["headers"])
    assert response.status_code == 200
    names = [s["file"] for s in response.json()["suggestions"]]

    assert names[:2] == ["Quantum notes.pdf", "quantum physics.docx"]
    assert "notes quantum.txt" in names and "Turing.pdf" not in names
    assert "quantum secret.pdf" not in names

    assert (
        client.get("/search/suggestions", params={"prefix": "q"}, headers=user["headers"]).json()["suggestions"] == []
    )
    assert client.get("/search/suggestions", params={"prefix": "quan"}).status_code == 401


def test_suggestion_prefix_wildcards_are_literal(client, user):

    add_point(user, "google_drive", "S-a", "abc.pdf", "document", "document", "text")

    response = client.get("/search/suggestions", params={"prefix": "%%"}, headers=user["headers"])

    assert response.json()["suggestions"] == []


def test_recent_files_are_the_last_eight_indexed_for_the_user(client, user, make_user):

    other = make_user()
    for i in range(10):
        add_point(user, "google_drive", f"R-{i}", f"file {i}.pdf", "document", "document", "text")
    add_point(other, "google_drive", "R-x", "not mine.pdf", "document", "document", "text")

    files = client.get("/dashboard/recent", headers=user["headers"]).json()["files"]

    assert [f["file"] for f in files] == [f"file {i}.pdf" for i in range(9, 1, -1)]
    assert client.get("/dashboard/recent").status_code == 401


def test_dashboard_stats_give_one_connection_count_and_per_platform_detail(client, user):

    add_point(user, "google_drive", "P-1", "a.pdf", "document", "document", "text")

    stats = client.get("/dashboard/stats", headers=user["headers"]).json()

    assert (stats["connected_platforms"], stats["supported_platforms"]) == (0, 3)
    drive = stats["platforms"]["google_drive"]
    assert drive["indexed_files"] == 1 and drive["last_indexed_at"].endswith("+00:00")
    assert stats["platforms"]["github"] == {"connected": False, "indexed_files": 0, "last_indexed_at": None}


# ---------------------------------------------------------------------------
# Phase 6C: video frames as evidence on their own
# ---------------------------------------------------------------------------


def video(file, frame_margin, null_mean=-0.01, null_std=0.01, frame_time=160):

    from app.search.retrieval import Candidate

    return Candidate(
        platform="google_drive",
        source_id=f"V-{file}",
        file=file,
        path=file,
        file_type="video",
        clip_margin=frame_margin,
        frame_number=frame_time // 5,
        frame_time_s=frame_time,
        frame_null_mean=null_mean,
        frame_null_std=null_std,
    )


def test_strong_frame_evidence_alone_returns_the_video_with_its_frame_time():

    from app.search.ranking import VIDEO_FRAME_Z_EVIDENCE, score_candidates

    # z = (margin - null_mean) / null_std, just above the evidence threshold
    margin = -0.01 + (VIDEO_FRAME_Z_EVIDENCE + 0.5) * 0.01
    scored = score_candidates([video("nature documentary.mp4", margin)], "polar bear cubs in the snow")

    assert [s.candidate.file for s in scored] == ["nature documentary.mp4"]
    assert scored[0].name == 0 and scored[0].content == 0  # no name, no transcript
    assert scored[0].reasons == ["visual"]
    assert scored[0].match["frame_time_s"] == 160


def test_weak_frame_evidence_only_boosts_and_never_returns_a_video_alone():

    from app.search.ranking import VIDEO_FRAME_Z_EVIDENCE, score_candidates

    margin = -0.01 + (VIDEO_FRAME_Z_EVIDENCE - 1) * 0.01
    assert score_candidates([video("nature documentary.mp4", margin)], "polar bear cubs") == []
    # A video without a stored null (not backfilled) is never returned on frames alone.
    assert score_candidates([video("old.mp4", 0.5, null_mean=None, null_std=None)], "polar bear") == []


def test_the_same_margin_means_less_on_a_video_whose_footage_matches_everything():

    from app.search.ranking import frame_z

    generic = video("b.mp4", 0.06, null_mean=0.02, null_std=0.01)  # high null: generic footage
    specific = video("a.mp4", 0.06, null_mean=-0.02, null_std=0.01)
    assert frame_z(specific) > frame_z(generic)


def test_null_stats_and_frame_timestamps():

    import numpy as np

    from app.search.frame_null import FRAME_INTERVAL_S, format_timestamp, frame_time_s, null_stats

    rng = np.random.default_rng(0)
    mean, std = null_stats(rng.normal(size=(20, 512)).tolist())
    assert mean is not None and std >= 1e-3
    assert null_stats([]) == (None, None)
    assert frame_time_s(32) == 32 * FRAME_INTERVAL_S == 160
    assert (format_timestamp(160), format_timestamp(3725), format_timestamp(None)) == ("2:40", "1:02:05", None)


def test_indexed_frames_store_their_time_and_the_video_null(client, user, local_root, monkeypatch):

    from pathlib import Path as P

    import app.services.indexers.video_indexer as video_indexer
    from app.vectorstore.client import get_client
    from app.vectorstore.config import collection_for_type

    folder = local_root / "videos-6c"
    folder.mkdir()

    def fake_frames(path, output_folder):
        P(output_folder).mkdir(parents=True)
        out = []
        for i, text in enumerate(["polar bear on snow", "penguins on ice", "a meerkat"]):
            frame = P(output_folder) / f"frame_{i}.jpg"
            frame.write_text(text)
            out.append(str(frame))
        return out

    monkeypatch.setattr(video_indexer, "extract_video_transcript", lambda path: "")
    monkeypatch.setattr(video_indexer, "extract_frames", fake_frames)
    clip = folder / "clip.mp4"
    clip.write_bytes(b"\x00")

    assert index_local_file(user["id"], str(clip)) == "indexed"

    points, _ = get_client().scroll(collection_for_type("video_frame"), limit=10, with_payload=True)
    mine = sorted((p.payload for p in points if p.payload["file"] == "clip.mp4"), key=lambda p: p["frame_number"])
    assert [p["frame_time_s"] for p in mine] == [0, 5, 10]
    assert all(p["null_mean"] is not None and p["null_std"] > 0 for p in mine)
    assert len({p["null_mean"] for p in mine}) == 1  # one null per video


# ---------------------------------------------------------------------------
# Phase 6D: "possible visual matches" (low-confidence tier)
# ---------------------------------------------------------------------------


def z_video(file, z, frame_time=20):
    # null mean 0, std 0.01 -> z = margin / 0.01
    return video(file, z * 0.01, null_mean=0.0, null_std=0.01, frame_time=frame_time)


@pytest.mark.parametrize("z, possible", [(2.99, False), (3.0, True), (4.5, True), (5.29, True), (5.3, False)])
def test_video_tier_boundaries(z, possible):

    from app.search.ranking import possible_visual_matches, score_candidates

    c = z_video("forest.mp4", z)
    returned = {s.candidate.key for s in score_candidates([c], "river")}
    tier = possible_visual_matches([c], returned)

    assert (len(tier) == 1) is possible
    if possible:
        assert tier[0].match["confidence"] == "low" and tier[0].match["frame_time_s"] == 20
    if z >= 5.3:
        assert returned  # a confident result, never also "possible"


@pytest.mark.parametrize("margin, possible", [(0.0149, False), (0.015, True), (0.0299, True), (0.03, False)])
def test_image_tier_boundaries(margin, possible):

    from app.search.ranking import possible_visual_matches, score_candidates

    c = image("IMG_1.webp", margin)
    returned = {s.candidate.key for s in score_candidates([c], "dog")}

    assert (len(possible_visual_matches([c], returned)) == 1) is possible


def test_document_photos_never_enter_the_tier():

    from app.search.ranking import possible_visual_matches

    page = " ".join(["candidate roll number examination centre subject"] * 5)
    assert possible_visual_matches([image("scan.jpeg", 0.02, ocr=page)], set()) == []


def test_tier_is_capped_at_three_and_sorted_by_score():

    from app.search.ranking import possible_visual_matches

    candidates = [z_video(f"v{i}.mp4", 3.0 + i * 0.4) for i in range(5)] + [image("a.webp", 0.016)]
    tier = possible_visual_matches(candidates, set())

    # Same score scale as confident results: an image at margin 0.016 (0.128) outranks a video at z 3.8 (0.107).
    assert [t.candidate.file for t in tier] == ["v4.mp4", "v3.mp4", "a.webp"]
    assert [t.score for t in tier] == sorted((t.score for t in tier), reverse=True)


def possible_api(client, user, monkeypatch, search_type="all", offset=0):

    import app.services.search_service as service

    candidates = [
        z_video("forest.mp4", 3.5),
        z_video("space.mp4", 4.0),
        image("lake.webp", 0.02),
        image("dog.webp", 0.06),
    ]  # dog.webp passes the gate: a confident result
    monkeypatch.setattr(service, "retrieve", lambda *a, **k: {c.key: c for c in candidates})

    response = client.post(
        "/search/", json={"query": "river", "search_type": search_type, "offset": offset}, headers=user["headers"]
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_api_possible_matches_are_separate_and_never_counted(client, user, monkeypatch):

    body = possible_api(client, user, monkeypatch)

    assert [r["file"] for r in body["results"]] == ["dog.webp"] and body["total"] == 1
    assert [r["file"] for r in body["possible_matches"]] == ["lake.webp", "space.mp4", "forest.mp4"]
    assert all(r["match"]["confidence"] == "low" for r in body["possible_matches"])
    assert "confidence" not in body["results"][0]["match"]
    assert body["possible_matches"][1]["match"]["frame_time_s"] == 20


@pytest.mark.parametrize("search_type, expected", [("document", 0), ("audio", 0), ("video", 3), ("image", 3)])
def test_api_possible_matches_only_for_visual_search_types(client, user, monkeypatch, search_type, expected):

    assert len(possible_api(client, user, monkeypatch, search_type)["possible_matches"]) == expected


def test_api_possible_matches_only_with_the_first_page(client, user, monkeypatch):

    assert possible_api(client, user, monkeypatch, offset=20)["possible_matches"] == []
