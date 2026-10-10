"""Phase 3: Qdrant as the only index, per-user isolation, ledger, deletion sync.

Runs against an in-memory Qdrant with a test_ prefix and a fake embedder.
"""

import os
import uuid
from pathlib import Path

import pytest

from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint
from app.services.indexing_pipeline import index_local_file, local_source_id
from app.vectorstore.client import get_client
from app.vectorstore.config import all_collections, collection_for_type
from app.vectorstore.query import MissingUserScope, search_points, user_filter
from tests.test_jobs import drain, enqueue, isolated_queue, jobs_of, make_worker  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def folder(local_root):

    path = local_root / f"docs-{uuid.uuid4().hex[:8]}"
    path.mkdir()
    return path


def write(path: Path, text: str) -> Path:

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def register(client, user, path):

    response = client.post("/platforms/local/folders", json={"folder": str(path)}, headers=user["headers"])
    assert response.status_code == 200, response.text


def search(client, user, query, debug=False, **params):

    url = "/search/?debug=true" if debug else "/search/"
    response = client.post(url, json={"query": query, **params}, headers=user["headers"])
    assert response.status_code == 200, response.text
    return response.json()["results"]


def count_points(user_id, platform=None, source_id=None, point_type="document"):

    extra = {"source_id": source_id} if source_id else {}

    return (
        get_client()
        .count(collection_for_type(point_type), count_filter=user_filter(str(user_id), platform, **extra), exact=True)
        .count
    )


def bump_mtime(path: Path):

    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 10))


# ---------------------------------------------------------------------------
# Isolation (SEC-03 real fix)
# ---------------------------------------------------------------------------


def test_two_users_with_identical_files_only_see_their_own(client, make_user, folder):

    alice, bob = make_user(), make_user()

    # Same folder, same file names and paths for both users.
    report = write(folder / "java notes.txt", "java streams lambdas collections")
    register(client, alice, folder)
    register(client, bob, folder)

    assert index_local_file(alice["id"], str(report)) == "indexed"

    assert [r["file"] for r in search(client, alice, "java")] == ["java notes.txt"]
    assert search(client, bob, "java") == []  # bob has not indexed it

    assert index_local_file(bob["id"], str(report)) == "indexed"

    alice_hits = search(client, alice, "java")
    bob_hits = search(client, bob, "java")
    assert len(alice_hits) == len(bob_hits) == 1

    # Separate points and ledger rows per user.
    source_id = local_source_id(str(report))
    assert count_points(alice["id"], "local", source_id) == 1
    assert count_points(bob["id"], "local", source_id) == 1

    stats_a = client.get("/dashboard/stats", headers=alice["headers"]).json()
    stats_b = client.get("/dashboard/stats", headers=bob["headers"]).json()
    assert stats_a["documents"] == stats_b["documents"] == 1

    # Alice removing the folder purges only Alice's copy.
    removed = client.request(
        "DELETE", "/platforms/local/folders", json={"folder": str(folder)}, headers=alice["headers"]
    )
    assert removed.json()["purged_files"] == 1
    assert search(client, alice, "java") == []
    assert len(search(client, bob, "java")) == 1


def test_fresh_user_gets_zero_results(client, make_user, folder):

    owner, stranger = make_user(), make_user()
    register(client, owner, folder)
    index_local_file(owner["id"], str(write(folder / "a.txt", "java java java")))

    assert search(client, stranger, "java") == []


def test_vector_queries_without_user_are_refused():

    with pytest.raises(MissingUserScope):
        search_points("document", [0.1] * 384, user_id=None)

    with pytest.raises(MissingUserScope):
        user_filter("")


def test_search_service_requires_a_user():

    from app.services.search_service import search as search_service

    with pytest.raises(ValueError):
        search_service("java", user_id=None)


# ---------------------------------------------------------------------------
# Deterministic ids, stale chunks, upsert-then-prune
# ---------------------------------------------------------------------------


def test_reindexing_overwrites_and_prunes_stale_chunks(user, folder):

    doc = write(folder / "long.txt", "alpha " * 600)  # 3600 chars -> 4 chunks of 1000
    source_id = local_source_id(str(doc))

    assert index_local_file(user["id"], str(doc)) == "indexed"
    assert count_points(user["id"], "local", source_id) == 4

    # Same file again (forced): same deterministic ids, no duplicates.
    index_local_file(user["id"], str(doc), force=True)
    assert count_points(user["id"], "local", source_id) == 4

    # Shorter file: chunks 2..3 must disappear.
    write(doc, "beta " * 300)  # 1500 chars -> 2 chunks
    bump_mtime(doc)
    assert index_local_file(user["id"], str(doc)) == "indexed"
    assert count_points(user["id"], "local", source_id) == 2

    row = index_store.get_source(user["id"], "local", source_id)
    assert (row.chunk_count, row.status) == (2, "indexed")


def test_point_ids_are_deterministic():

    from app.vectorstore.schema import point_id

    a = point_id("u", "local", "c:\\x.txt", "document", 0)
    assert a == point_id("u", "local", "c:\\x.txt", "document", 0)
    assert a != point_id("other", "local", "c:\\x.txt", "document", 0)
    assert a != point_id("u", "local", "c:\\x.txt", "document", 1)
    assert point_id("u", "local", "v", "video_frame", 3, 3) != point_id("u", "local", "v", "video_frame", 3, None)


def test_upsert_writes_new_points_before_pruning(user, monkeypatch):

    client = get_client()
    calls = []

    original_upsert, original_delete = client.upsert, client.delete

    def spy_upsert(*args, **kwargs):
        calls.append("upsert")
        return original_upsert(*args, **kwargs)

    def spy_delete(*args, **kwargs):
        calls.append("delete")
        return original_delete(*args, **kwargs)

    monkeypatch.setattr(client, "upsert", spy_upsert)
    monkeypatch.setattr(client, "delete", spy_delete)

    meta = FileMeta(
        user_id=user["id"],
        platform="google_drive",
        source_id="D1",
        file_name="d.docx",
        display_path="d.docx",
        file_type="document",
        version="v1",
    )
    index_store.upsert_file(meta, [IndexPoint("document", [1.0] + [0.0] * 383, 0, "x")])

    assert calls == ["upsert", "delete"]


def test_payload_has_exactly_the_v2_schema(user, folder):

    doc = write(folder / "schema.md", "# Title\n\nsome markdown text")
    index_local_file(user["id"], str(doc))

    points, _ = get_client().scroll(
        collection_for_type("document"),
        scroll_filter=user_filter(user["id"], "local", source_id=local_source_id(str(doc))),
        with_payload=True,
        with_vectors=False,
    )

    payload = points[0].payload
    assert set(payload) == {
        "user_id",
        "platform",
        "source_id",
        "file",
        "path",
        "type",
        "version",
        "chunk_index",
        "chunk",
    }
    assert payload["type"] == "document"
    assert payload["file"] == "schema.md"
    assert payload["path"] == os.path.realpath(doc)
    assert isinstance(payload["version"], float)
    assert payload["user_id"] == user["id"]


# ---------------------------------------------------------------------------
# needs_index (BUG-16)
# ---------------------------------------------------------------------------


def test_unchanged_files_are_skipped_and_empty_files_not_reprocessed(user, folder, monkeypatch):

    import app.services.indexing_pipeline as pipeline

    calls = []
    original = pipeline.BUILDERS["document"]

    def counting(path, temp_dir=None):
        calls.append(Path(path).name)
        return original(path, temp_dir)

    monkeypatch.setitem(pipeline.BUILDERS, "document", counting)

    full = write(folder / "full.txt", "content here")
    empty = write(folder / "empty.txt", "   \n  ")

    assert index_local_file(user["id"], str(full)) == "indexed"
    assert index_local_file(user["id"], str(empty)) == "no_content"

    assert index_local_file(user["id"], str(full)) == "skipped"
    assert index_local_file(user["id"], str(empty)) == "skipped"
    assert calls == ["full.txt", "empty.txt"]

    write(full, "changed content")
    bump_mtime(full)
    assert index_local_file(user["id"], str(full)) == "indexed"
    assert calls == ["full.txt", "empty.txt", "full.txt"]


# ---------------------------------------------------------------------------
# Deletion sync
# ---------------------------------------------------------------------------


def test_local_job_removes_deleted_files_and_unregistered_folders(client, make_user, folder, local_root):

    from app.platforms.local.local_platform import LocalPlatform

    alice, bob = make_user(), make_user()

    write(folder / "keep.txt", "java keep")
    gone = write(folder / "gone.txt", "java gone")
    other_folder = local_root / f"other-{uuid.uuid4().hex[:6]}"
    elsewhere = write(other_folder / "elsewhere.txt", "java elsewhere")

    register(client, alice, folder)
    register(client, alice, other_folder)
    register(client, bob, folder)

    worker = make_worker(local=LocalPlatform)
    enqueue(client, alice, ["local"])
    drain(worker)
    enqueue(client, bob, ["local"])
    drain(worker)

    assert {r["file"] for r in search(client, alice, "java")} == {"keep.txt", "gone.txt", "elsewhere.txt"}

    gone.unlink()
    client.request("DELETE", "/platforms/local/folders", json={"folder": str(other_folder)}, headers=alice["headers"])

    enqueue(client, alice, ["local"])
    drain(worker)

    assert {r["file"] for r in search(client, alice, "java")} == {"keep.txt"}
    assert index_store.get_source(alice["id"], "local", local_source_id(str(gone))) is None
    assert index_store.get_source(alice["id"], "local", local_source_id(str(elsewhere))) is None

    # Bob's rows for the same paths were not touched by Alice's sync; his own
    # next run removes his copy of the deleted file.
    assert index_store.get_source(bob["id"], "local", local_source_id(str(gone))) is not None
    enqueue(client, bob, ["local"])
    drain(worker)
    assert {r["file"] for r in search(client, bob, "java")} == {"keep.txt"}


def test_disconnect_with_purge_removes_platform_sources(client, user, monkeypatch):

    import app.routes.github as github_route

    monkeypatch.setattr(github_route, "disconnect_github", lambda db, user_id: None)

    for source in ("octo/app:a.txt", "octo/app:b.txt"):
        meta = FileMeta(
            user_id=user["id"],
            platform="github",
            source_id=source,
            file_name=source[-5:],
            display_path=source.replace(":", "/"),
            file_type="document",
            version="sha",
            owner="octo",
            repo="app",
        )
        index_store.upsert_file(meta, [IndexPoint("document", [1.0] + [0.0] * 383, 0, "x")])

    keep = client.post("/platforms/github/disconnect", headers=user["headers"]).json()
    assert keep["purged_files"] == 0
    assert len(index_store.list_sources(user["id"], "github")) == 2

    purged = client.post("/platforms/github/disconnect?purge=true", headers=user["headers"]).json()
    assert purged["purged_files"] == 2
    assert index_store.list_sources(user["id"], "github") == []
    assert count_points(user["id"], "github") == 0


def test_delete_file_removes_points_from_every_collection(user):

    meta = FileMeta(
        user_id=user["id"],
        platform="google_drive",
        source_id="V1",
        file_name="clip.mp4",
        display_path="clip.mp4",
        file_type="video",
        version="t",
    )
    index_store.upsert_file(
        meta,
        [
            IndexPoint("video", [1.0] + [0.0] * 383, 0, "spoken words"),
            IndexPoint("video_frame", [1.0] + [0.0] * 511, 0, "Frame 0", frame_number=0),
            IndexPoint("video_frame", [0.0, 1.0] + [0.0] * 510, 1, "Frame 1", frame_number=1),
        ],
    )

    assert count_points(user["id"], "google_drive", "V1", "video") == 1
    assert count_points(user["id"], "google_drive", "V1", "video_frame") == 2

    index_store.delete_file(user["id"], "google_drive", "V1")

    for point_type in ("video", "video_frame"):
        assert count_points(user["id"], "google_drive", "V1", point_type) == 0
    assert index_store.get_source(user["id"], "google_drive", "V1") is None


# ---------------------------------------------------------------------------
# Search correctness
# ---------------------------------------------------------------------------


def test_same_basename_in_two_folders_is_scored_independently(client, user, local_root):

    first = local_root / f"a-{uuid.uuid4().hex[:6]}"
    second = local_root / f"b-{uuid.uuid4().hex[:6]}"

    # Both mention "calculator" (so both clear the unchanged 0.30 threshold);
    # only the first also matches "kubernetes". The old basename-keyed caches
    # gave both files the same merged content score (BUG-20).
    write(first / "Calculator.txt", "calculator for kubernetes deployment yaml manifest")
    write(second / "Calculator.txt", "calculator for a chocolate cake recipe with sugar")

    register(client, user, first)
    register(client, user, second)
    index_local_file(user["id"], str(first / "Calculator.txt"))
    index_local_file(user["id"], str(second / "Calculator.txt"))

    results = search(client, user, "calculator kubernetes", search_type="document", debug=True)
    paths = {Path(r["path"]).parent.name: r for r in results}

    assert len(results) == 2
    assert paths[first.name]["debug"]["content"] > paths[second.name]["debug"]["content"]
    assert Path(results[0]["path"]).parent.name == first.name  # better match ranks first
    assert paths[first.name]["source_id"] != paths[second.name]["source_id"]


def test_video_transcript_drives_semantic_and_content_scores(client, user, folder, monkeypatch):

    import app.services.indexers.video_indexer as video_indexer

    def fake_frames(path, output_folder):
        Path(output_folder).mkdir(parents=True)
        frame = Path(output_folder) / "frame_0.jpg"
        frame.write_text("sunset over the ocean")
        return [str(frame)]

    monkeypatch.setattr(
        video_indexer, "extract_video_transcript", lambda path: "today we explain photosynthesis in green plants"
    )
    monkeypatch.setattr(video_indexer, "extract_frames", fake_frames)

    video = folder / "lecture.mp4"
    video.write_bytes(b"\x00")
    register(client, user, folder)

    assert index_local_file(user["id"], str(video)) == "indexed"

    results = search(client, user, "photosynthesis plants", search_type="video", debug=True)

    assert len(results) == 1
    result = results[0]
    assert result["debug"]["semantic"] > 0
    assert result["debug"]["content"] > 0
    assert "transcript" in result["match"]["reasons"]
    assert result["source_id"] == local_source_id(str(video))
    assert count_points(user["id"], "local", result["source_id"], "video_frame") == 1


def test_markdown_is_indexed_as_a_document(client, user, folder):

    note = write(folder / "README.md", "# Setup\n\nInstall the dependencies with pip")
    register(client, user, folder)

    assert index_local_file(user["id"], str(note)) == "indexed"

    row = index_store.get_source(user["id"], "local", local_source_id(str(note)))
    assert row.file_type == "document"

    assert [r["file"] for r in search(client, user, "install dependencies")] == ["README.md"]


def test_results_are_deduplicated_and_carry_identity(client, user, folder):

    doc = write(folder / "java guide.txt", ("java " * 300) + " streams")
    register(client, user, folder)
    index_local_file(user["id"], str(doc))

    results = search(client, user, "java")

    assert len(results) == 1
    result = results[0]
    for key in ("source_id", "platform", "type", "file", "path", "score"):
        assert key in result
    assert len({(r["platform"], r["source_id"], r["type"]) for r in results}) == len(results)


# ---------------------------------------------------------------------------
# Ownership of /open and /files/local
# ---------------------------------------------------------------------------


def test_open_is_404_for_another_users_sources(client, make_user, folder):

    owner, other = make_user(), make_user()

    doc = write(folder / "secret.txt", "private")
    register(client, owner, folder)
    register(client, other, folder)  # other can see the folder, but has not indexed it
    index_local_file(owner["id"], str(doc))

    gh = FileMeta(
        user_id=owner["id"],
        platform="github",
        source_id="octo/app:src/x.py",
        file_name="x.py",
        display_path="octo/app/src/x.py",
        file_type="document",
        version="sha",
        owner="octo",
        repo="app",
    )
    index_store.upsert_file(gh, [IndexPoint("document", [1.0] + [0.0] * 383, 0, "x")])

    for body in (
        {"platform": "local", "path": str(doc)},
        {"platform": "github", "source_id": "octo/app:src/x.py"},
    ):
        assert client.post("/open/", json=body, headers=other["headers"]).status_code == 404
        assert client.post("/open/", json=body, headers=owner["headers"]).status_code == 200

    owner_github = client.post(
        "/open/", json={"platform": "github", "source_id": "octo/app:src/x.py"}, headers=owner["headers"]
    ).json()
    assert owner_github == {"type": "url", "url": "https://github.com/octo/app/blob/main/src/x.py"}

    download = client.get("/files/local", params={"path": str(doc)}, headers=other["headers"])
    assert download.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_counts_are_per_user(client, make_user, folder, monkeypatch):

    import app.services.indexing_pipeline as pipeline

    user, other = make_user(), make_user()
    register(client, user, folder)

    index_local_file(user["id"], str(write(folder / "a.txt", "text a")))
    index_local_file(user["id"], str(write(folder / "b.md", "text b")))
    index_local_file(user["id"], str(write(folder / "empty.txt", " ")))

    def broken(path, temp_dir=None):
        raise RuntimeError("boom")

    monkeypatch.setitem(pipeline.BUILDERS, "document", broken)
    with pytest.raises(RuntimeError):
        index_local_file(user["id"], str(write(folder / "bad.txt", "x")))

    stats = client.get("/dashboard/stats", headers=user["headers"]).json()
    assert (stats["total_files"], stats["documents"], stats["no_content_files"], stats["failed_files"]) == (2, 2, 1, 1)
    assert stats["by_platform"]["local"] == 2
    assert stats["connected_platforms"] == 1  # local folders only
    assert stats["ready_platforms"] == 1
    assert stats["last_indexed_at"] is not None

    empty = client.get("/dashboard/stats", headers=other["headers"]).json()
    assert (empty["total_files"], empty["connected_platforms"]) == (0, 0)


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


def test_ensure_collections_is_idempotent():

    from app.vectorstore.schema import ensure_collections

    ensure_collections()
    assert ensure_collections() == []

    names = {c.name for c in get_client().get_collections().collections}
    assert set(all_collections()) <= names
    assert all(name.startswith("test_") for name in all_collections())
