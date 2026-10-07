"""Phase 5 bug #4: large/generated files - batched upserts, limits, exclusions."""

import uuid
from pathlib import Path

import pytest

from app.database.db import SessionLocal
from app.database.models import IndexedFile, IndexingJob, IndexingJobError
from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint, VectorStoreWriteError
from app.vectorstore.client import get_client
from app.vectorstore.config import collection_for_type
from app.vectorstore.query import user_filter
from tests.conftest import _bag_of_words_vector


VECTOR = _bag_of_words_vector("large generated text", 384)


def meta_for(user, version="v1", source_id=None, file_name="import_log.txt"):

    return FileMeta(user_id=user["id"], platform="github", source_id=source_id or f"me/repo:{uuid.uuid4().hex}",
                    file_name=file_name, display_path=f"me/repo/{file_name}", file_type="document", version=version)


def points(n):

    return [IndexPoint("document", VECTOR, i, f"chunk {i}") for i in range(n)]


def count(user, source_id):

    return get_client().count(
        collection_for_type("document"),
        count_filter=user_filter(str(user["id"]), "github", source_id=source_id),
        exact=True
    ).count


class CountingUpserts:
    """Wraps client.upsert: counts calls and can fail on the Nth one."""

    def __init__(self, monkeypatch, fail_on=None):

        self.client = get_client()
        self.real = self.client.upsert
        self.calls = []
        self.fail_on = fail_on
        monkeypatch.setattr(self.client, "upsert", self)

    def __call__(self, **kwargs):

        self.calls.append(len(kwargs["points"]))
        if self.fail_on == len(self.calls):
            raise ConnectionAbortedError("[WinError 10053] An established connection was aborted")
        return self.real(**kwargs)


def test_ten_thousand_chunks_upsert_in_batches_with_the_exact_count(user, monkeypatch):

    from app.core.config import settings

    upserts = CountingUpserts(monkeypatch)
    meta = meta_for(user)

    row = index_store.upsert_file(meta, points(10_000))

    batch = settings.QDRANT_UPSERT_BATCH
    assert len(upserts.calls) == -(-10_000 // batch) > 1
    assert max(upserts.calls) <= batch
    assert count(user, meta.source_id) == 10_000
    assert (row.status, row.chunk_count) == ("indexed", 10_000)


def test_a_failed_batch_prunes_nothing_and_records_failed(user, monkeypatch):

    meta = meta_for(user, version="v1")
    index_store.upsert_file(meta, points(1200))

    CountingUpserts(monkeypatch, fail_on=3)

    with pytest.raises(VectorStoreWriteError, match=r"^Could not save vectors \(request too large\)$"):
        index_store.upsert_file(meta_for(user, version="v2", source_id=meta.source_id), points(1000))

    # No prune: the old version's chunks 1000..1199 are still there.
    assert count(user, meta.source_id) == 1200

    row = index_store.get_source(user["id"], "github", meta.source_id)
    assert (row.status, row.version, row.chunk_count) == ("failed", "v1", 1200)
    assert row.error == "Could not save vectors (request too large)"
    # failed -> retried on the next run
    assert index_store.needs_index(user["id"], "github", meta.source_id, "v2")


def test_text_beyond_the_limits_is_truncated_with_a_ledger_note(user, local_root, monkeypatch):

    from app.core.config import settings
    from app.services.indexing_pipeline import index_local_file, local_source_id

    monkeypatch.setattr(settings, "MAX_CHUNKS_PER_FILE", 5)

    path = local_root / f"big-{uuid.uuid4().hex[:6]}" / "project_files.txt"
    path.parent.mkdir()
    path.write_text("word " * 4000, encoding="utf-8")       # 20,000 chars = 20 chunks

    assert index_local_file(user["id"], str(path)) == "indexed"

    row = index_store.get_source(user["id"], "local", local_source_id(str(path)))
    assert (row.status, row.chunk_count) == ("indexed", 5)
    assert row.error == "truncated: first 5,000 of 20,000 characters indexed"


def job_context(user, platform):

    from app.scheduler.context import JobContext

    job_id = uuid.uuid4()
    with SessionLocal() as session:
        session.add(IndexingJob(id=job_id, user_id=user["id"], platform=platform, status="running"))
        session.commit()

    return JobContext(job_id, user["id"], platform, Path("unused"))


@pytest.mark.parametrize("name", ["build.log", "yarn.lock", "app.min.js", "bundle.js.map"])
def test_generated_files_are_excluded_and_never_downloaded(user, name):

    from app.platforms.sync import RemoteFile, sync_remote

    ctx = job_context(user, "github")
    meta = meta_for(user, file_name=name)
    meta.file_type = "document" if name.endswith(".js") else "unsupported"

    def download(target):
        raise AssertionError("an excluded file must not be downloaded")

    result = sync_remote(ctx, "github", [RemoteFile(meta, ".x", 10, download)], listing_complete=False)

    assert (result.skipped, result.to_index) == (1, 0)
    row = index_store.get_source(user["id"], "github", meta.source_id)
    assert (row.status, row.error) == ("excluded", "excluded")
    assert not index_store.needs_index(user["id"], "github", meta.source_id, meta.version)


def test_local_excluded_files_are_recorded_and_skipped(user, local_root):

    from app.platforms.local.local_platform import LocalPlatform
    from app.services.indexing_pipeline import local_source_id

    folder = local_root / f"gen-{uuid.uuid4().hex[:6]}"
    folder.mkdir()
    (folder / "vendor.min.js").write_text("var a=1;", encoding="utf-8")
    (folder / "notes.txt").write_text("real notes", encoding="utf-8")

    ctx = job_context(user, "local")

    from unittest.mock import patch
    with patch("app.platforms.local.local_platform.get_local_folders",
               return_value=[type("F", (), {"folder_path": str(folder)})()]):
        LocalPlatform().index(ctx)

    assert index_store.get_source(user["id"], "local", local_source_id(str(folder / "vendor.min.js"))).status == "excluded"
    assert index_store.get_source(user["id"], "local", local_source_id(str(folder / "notes.txt"))).status == "indexed"
    assert ctx.failed_files == 0


def test_job_errors_show_the_friendly_message_only(user):

    from app.platforms.indexing import process_files

    ctx = job_context(user, "github")

    def handle(_position, _item):
        raise VectorStoreWriteError("Could not save vectors (request too large)")

    process_files(ctx, ["me/repo/import_log.txt"], file_ref=str, handle=handle)

    with SessionLocal() as session:
        errors = [e.error for e in session.query(IndexingJobError).filter_by(job_id=ctx.job_id)]

    assert errors == ["Could not save vectors (request too large)"]
