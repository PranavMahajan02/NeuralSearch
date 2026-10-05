"""DB-backed job queue, worker, JobContext (BUG-01, 06, 13, 14, 15, 18, 19).

Platforms are fakes; the worker runs synchronously via run_once() except in
the thread test. No model is loaded and the owner's data is never touched.
"""

import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from app.database.models import IndexingJob, IndexingJobError
from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import process_files
from app.scheduler import jobs as job_service
from app.scheduler.worker import IndexingWorker


# ---------------------------------------------------------------------------
# Fakes and helpers
# ---------------------------------------------------------------------------

class FakePlatform:
    """Processes `files`; any name in `fail` raises; `on_file` hooks run first."""

    calls = []

    def __init__(self, files=("a.txt", "b.txt", "c.txt"), fail=(), on_file=None, skipped=0):

        self.files = list(files)
        self.fail = set(fail)
        self.on_file = on_file
        self.skipped = skipped

    def index(self, ctx):

        FakePlatform.calls.append((ctx.platform, str(ctx.job_id)))

        ctx.add_skipped(self.skipped)
        ctx.set_total(len(self.files))

        def handle(position, name):
            if self.on_file:
                self.on_file(ctx, position, name)
            if name in self.fail:
                raise ValueError(f"cannot parse {name}")

        process_files(ctx, self.files, file_ref=lambda name: name, handle=handle)


class Exploding:

    def index(self, ctx):
        raise RuntimeError("boom at C:\\Users\\someone\\secret.pdf with token=abc123")


class NotConnected:

    def index(self, ctx):
        raise PlatformPreconditionError("Google Drive is not connected.")


def make_worker(**factories):

    defaults = {"local": FakePlatform, "google_drive": FakePlatform, "github": FakePlatform}
    defaults.update(factories)

    return IndexingWorker(platform_factories=defaults, poll_interval=0.05)


def enqueue(client, user, platforms, priority=None):

    return client.post(
        "/index/",
        json={"priority_platform": priority or platforms[0], "platforms": platforms},
        headers=user["headers"]
    )


def jobs_of(client, user):

    response = client.get("/index/jobs", headers=user["headers"])
    assert response.status_code == 200
    return {job["platform"]: job for job in response.json()}


@pytest.fixture(autouse=True)
def isolated_queue(db):
    """Each test starts with no queued/running jobs from other tests."""

    db.query(IndexingJob).filter(IndexingJob.status.in_(("queued", "running"))).update(
        {IndexingJob.status: "cancelled"}, synchronize_session=False
    )
    db.commit()

    FakePlatform.calls = []

    yield


def drain(worker, limit=20):

    runs = 0
    while worker.run_once():
        runs += 1
        assert runs < limit


# ---------------------------------------------------------------------------
# Enqueue / validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    {"priority_platform": "dropbox", "platforms": ["dropbox"]},
    {"priority_platform": "local", "platforms": ["local", "Local"]},
    {"priority_platform": "local", "platforms": []},
])
def test_invalid_platforms_are_422(client, user, body):

    response = client.post("/index/", json=body, headers=user["headers"])

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_enqueue_creates_new_queued_jobs_priority_first(client, user, db):

    response = enqueue(client, user, ["local", "github", "local"], priority="github")

    assert response.status_code == 200
    assert response.json()["platforms"] == ["github", "local"]

    rows = (
        db.query(IndexingJob)
        .filter(IndexingJob.user_id == user["id"])
        .order_by(IndexingJob.created_at)
        .all()
    )
    assert [(r.platform, r.status) for r in rows] == [("github", "queued"), ("local", "queued")]

    current = jobs_of(client, user)
    assert current["github"]["status"] == "queued"
    for field in ("processed_files", "succeeded_files", "failed_files", "skipped_files",
                  "error_message", "cancel_requested", "heartbeat_at", "created_at", "id"):
        assert field in current["github"]


def test_duplicate_enqueue_is_409_and_creates_nothing(client, user, db):

    assert enqueue(client, user, ["local"]).status_code == 200

    response = enqueue(client, user, ["github", "local"])

    assert response.status_code == 409
    assert response.json()["code"] == "job_already_active"
    assert "local" in response.json()["detail"]

    platforms = [r.platform for r in db.query(IndexingJob).filter(IndexingJob.user_id == user["id"])]
    assert platforms == ["local"]


def test_finished_jobs_are_kept_as_history(client, user, db):

    worker = make_worker()

    for _ in range(3):
        assert enqueue(client, user, ["local"]).status_code == 200
        drain(worker)

    rows = db.query(IndexingJob).filter(IndexingJob.user_id == user["id"]).all()
    assert len(rows) == 3
    assert {r.status for r in rows} == {"completed"}


def test_db_enforces_one_active_job_per_platform(user, db):

    from sqlalchemy.exc import IntegrityError

    db.add(IndexingJob(user_id=user["id"], platform="local", status="queued"))
    db.add(IndexingJob(user_id=user["id"], platform="local", status="running"))

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


# ---------------------------------------------------------------------------
# Worker: outcomes
# ---------------------------------------------------------------------------

def test_successful_job_is_completed_with_accurate_counters(client, user):

    enqueue(client, user, ["local"])

    drain(make_worker(local=lambda: FakePlatform(skipped=4)))

    job = jobs_of(client, user)["local"]
    assert job["status"] == "completed"
    assert (job["total_files"], job["processed_files"], job["succeeded_files"],
            job["failed_files"], job["skipped_files"]) == (3, 3, 3, 0, 4)
    assert job["progress"] == 100
    assert job["error_message"] is None
    assert job["completed_at"] is not None


def test_per_file_error_gives_completed_with_errors(client, user):

    enqueue(client, user, ["local"])

    drain(make_worker(local=lambda: FakePlatform(fail={"b.txt"})))

    job = jobs_of(client, user)["local"]
    assert job["status"] == "completed_with_errors"
    assert (job["succeeded_files"], job["failed_files"], job["processed_files"]) == (2, 1, 3)

    errors = client.get(f"/index/jobs/{job['id']}/errors", headers=user["headers"])
    assert errors.status_code == 200
    assert errors.json()["errors"] == [
        {"file": "b.txt", "error": "ValueError: cannot parse b.txt", "created_at": errors.json()["errors"][0]["created_at"]}
    ]


def test_all_files_failing_is_failed(client, user):

    enqueue(client, user, ["local"])

    drain(make_worker(local=lambda: FakePlatform(fail={"a.txt", "b.txt", "c.txt"})))

    job = jobs_of(client, user)["local"]
    assert job["status"] == "failed"
    assert job["error_message"] == "All 3 files failed to index."
    assert job["failed_files"] == 3


def test_empty_platform_is_completed(client, user):

    enqueue(client, user, ["local"])

    drain(make_worker(local=lambda: FakePlatform(files=())))

    job = jobs_of(client, user)["local"]
    assert (job["status"], job["total_files"], job["progress"]) == ("completed", 0, 0)


def test_worker_survives_a_crashing_platform_and_runs_the_next_job(client, user):

    enqueue(client, user, ["local", "github"])

    worker = make_worker(local=Exploding)

    assert worker.run_once() is True     # local crashes
    assert worker.run_once() is True     # github still runs
    assert worker.run_once() is False    # queue empty

    jobs = jobs_of(client, user)
    assert jobs["local"]["status"] == "failed"
    # Exception type + message, with the out-of-scope path and the token removed.
    assert jobs["local"]["error_message"] == "RuntimeError: boom at <path> with token=<redacted>"
    assert jobs["github"]["status"] == "completed"


def test_worker_thread_never_dies(client, user):

    worker = make_worker(local=Exploding)
    worker.start()

    try:
        enqueue(client, user, ["local", "github"])
        worker.notify()

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            states = {j["platform"]: j["status"] for j in jobs_of(client, user).values()}
            if states.get("github") == "completed":
                break
            time.sleep(0.05)

        assert states == {"local": "failed", "github": "completed"}
        assert worker.is_alive
    finally:
        worker.stop()

    assert not worker.is_alive


def test_worker_loop_survives_db_errors(monkeypatch):

    worker = make_worker()
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database is down")
        worker._stop.set()
        return False

    monkeypatch.setattr(worker, "run_once", flaky)
    monkeypatch.setattr("app.scheduler.worker.LOOP_ERROR_BACKOFF_SECONDS", 0.01)

    worker._run_forever()   # returns only because flaky() sets the stop flag

    assert len(calls) == 2


def test_precondition_failure_fails_the_job_with_a_clear_message(client, user):

    enqueue(client, user, ["google_drive"])

    drain(make_worker(google_drive=NotConnected))

    job = jobs_of(client, user)["google_drive"]
    assert job["status"] == "failed"
    assert job["error_message"] == "PlatformPreconditionError: Google Drive is not connected."


def test_real_drive_platform_without_connection_fails_cleanly(client, user):

    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    enqueue(client, user, ["google_drive"])

    drain(make_worker(google_drive=GoogleDrivePlatform))

    job = jobs_of(client, user)["google_drive"]
    assert (job["status"], job["error_message"]) == (
        "failed", "PlatformPreconditionError: Google Drive is not connected."
    )


def test_real_github_platform_without_connection_fails_cleanly(client, user):

    from app.platforms.github.github_platform import GitHubPlatform

    enqueue(client, user, ["github"])

    drain(make_worker(github=GitHubPlatform))

    job = jobs_of(client, user)["github"]
    assert (job["status"], job["error_message"]) == (
        "failed", "PlatformPreconditionError: GitHub is not connected."
    )


def test_precondition_raised_mid_run_aborts_the_job(client, user):

    def lose_auth(ctx, position, name):
        if position == 1:
            raise PlatformPreconditionError("GitHub authentication failed. Please reconnect GitHub.")

    enqueue(client, user, ["github"])

    drain(make_worker(github=lambda: FakePlatform(on_file=lose_auth)))

    job = jobs_of(client, user)["github"]
    assert job["status"] == "failed"
    assert job["succeeded_files"] == 1
    assert "reconnect GitHub" in job["error_message"]


def test_error_storage_is_capped(client, user, db):

    names = [f"f{i}.txt" for i in range(205)]

    enqueue(client, user, ["local"])

    drain(make_worker(local=lambda: FakePlatform(files=names, fail=set(names[:-1]))))

    job = jobs_of(client, user)["local"]
    assert (job["failed_files"], job["succeeded_files"], job["status"]) == (204, 1, "completed_with_errors")

    stored = db.query(IndexingJobError).filter(IndexingJobError.job_id == job["id"]).count()
    assert stored == 200


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def test_cancel_mid_run_stops_after_current_file_and_cancels_queued(client, user):

    def cancel_during_second_file(ctx, position, name):
        if position == 1:
            response = client.post(f"/index/jobs/{ctx.job_id}/cancel", headers=user["headers"])
            assert response.status_code == 200
            assert response.json()["cancel_requested"] is True

    enqueue(client, user, ["local", "github"])

    worker = make_worker(local=lambda: FakePlatform(on_file=cancel_during_second_file))
    drain(worker)

    jobs = jobs_of(client, user)
    assert jobs["local"]["status"] == "cancelled"
    # File 2 finished (current file), file 3 never started.
    assert jobs["local"]["processed_files"] == 2
    assert jobs["github"]["status"] == "cancelled"
    assert ("github", jobs["github"]["id"]) not in FakePlatform.calls


def test_cancel_queued_job_directly(client, user):

    enqueue(client, user, ["local", "github"])
    github = jobs_of(client, user)["github"]

    response = client.post(f"/index/jobs/{github['id']}/cancel", headers=user["headers"])

    assert response.json()["status"] == "cancelled"
    assert jobs_of(client, user)["local"]["status"] == "queued"


def test_logout_cancels_queued_and_running_jobs(client, make_user, db):

    user = make_user()

    enqueue(client, user, ["local", "github"])

    with job_service_session(db) as session:
        running = job_service.claim_next_job(session)
    assert running.platform == "local"

    assert client.post("/auth/logout", headers=user["headers"]).status_code == 200

    db.expire_all()
    rows = {r.platform: r for r in db.query(IndexingJob).filter(IndexingJob.user_id == user["id"])}
    assert rows["github"].status == "cancelled"
    assert rows["local"].status == "running" and rows["local"].cancel_requested is True

    # The worker then finalizes the running job as cancelled.
    with job_service_session(db) as session:
        assert job_service.finalize_job(session, rows["local"].id).status == "cancelled"


class job_service_session:

    def __init__(self, db):
        from app.database.db import SessionLocal
        self.session = SessionLocal()

    def __enter__(self):
        return self.session

    def __exit__(self, *exc):
        self.session.close()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def test_other_users_jobs_are_invisible(client, make_user):

    alice, bob = make_user(), make_user()

    enqueue(client, alice, ["local"])
    drain(make_worker(local=lambda: FakePlatform(fail={"a.txt"})))
    alice_job = jobs_of(client, alice)["local"]

    assert jobs_of(client, bob) == {}

    for method, path in (
        ("GET", f"/index/jobs/{alice_job['id']}/errors"),
        ("POST", f"/index/jobs/{alice_job['id']}/cancel"),
        ("GET", f"/index/jobs/{uuid.uuid4()}/errors"),
    ):
        response = client.request(method, path, headers=bob["headers"])
        assert response.status_code == 404
        assert response.json() == {"detail": "Job not found.", "code": "not_found"}

    assert client.get(f"/index/jobs/{alice_job['id']}/errors", headers=alice["headers"]).status_code == 200


# ---------------------------------------------------------------------------
# Startup recovery
# ---------------------------------------------------------------------------

def test_startup_recovery_fails_running_jobs_and_keeps_queued(app, user, db):

    from fastapi.testclient import TestClient

    running = IndexingJob(user_id=user["id"], platform="local", status="running", started_at=datetime.utcnow())
    queued = IndexingJob(user_id=user["id"], platform="github", status="queued")
    db.add_all([running, queued])
    db.commit()

    # A fresh app lifespan = a server restart.
    with TestClient(app):
        pass

    db.expire_all()
    assert db.get(IndexingJob, running.id).status == "failed"
    assert db.get(IndexingJob, running.id).error_message == "Interrupted by server restart"
    assert db.get(IndexingJob, queued.id).status == "queued"


# ---------------------------------------------------------------------------
# Temp dirs
# ---------------------------------------------------------------------------

def test_job_temp_dir_is_created_and_removed_even_on_exception(client, user):

    seen = {}

    class UsesTemp:
        def index(self, ctx):
            seen["dir"] = ctx.temp_dir
            assert ctx.temp_dir.is_dir()
            assert ctx.temp_dir.name == str(ctx.job_id)
            assert ctx.temp_dir.parent.name == "jobs"
            (ctx.file_dir(0) / "download.bin").write_bytes(b"x")
            ctx.frames_dir.mkdir()
            raise RuntimeError("crash after writing temp files")

    enqueue(client, user, ["local"])
    drain(make_worker(local=UsesTemp))

    assert jobs_of(client, user)["local"]["status"] == "failed"
    assert not seen["dir"].exists()


def test_video_frames_go_to_a_private_dir_that_is_removed(monkeypatch, tmp_path):

    import app.services.indexers.video_indexer as video_indexer

    used = []

    def fake_extract_frames(path, output_folder):
        used.append(Path(output_folder))
        Path(output_folder).mkdir(parents=True)
        (Path(output_folder) / "frame_0.jpg").write_bytes(b"x")
        raise RuntimeError("decoder failed")

    monkeypatch.setattr(video_indexer, "delete_vectors", lambda **kwargs: None)
    monkeypatch.setattr(video_indexer, "extract_video_text", lambda path: "")
    monkeypatch.setattr(video_indexer, "extract_frames", fake_extract_frames)

    for _ in range(2):
        with pytest.raises(RuntimeError, match="decoder failed"):
            video_indexer.index_video(str(tmp_path / "clip.mp4"), frames_root=tmp_path / "job")

    assert used[0] != used[1]
    assert all(path.parent == tmp_path / "job" and path.name.startswith("frames-") for path in used)
    assert not any(path.exists() for path in used)


# ---------------------------------------------------------------------------
# Real local platform: counting + per-file errors
# ---------------------------------------------------------------------------

def test_local_platform_counts_only_supported_files(client, user, local_root, monkeypatch):

    import app.services.index_manager as index_manager
    import app.services.upload_service as upload_service

    folder = local_root / f"index-me-{uuid.uuid4().hex[:6]}"
    (folder / "sub" / "deeper").mkdir(parents=True)
    for name in ("a.pdf", "b.txt", "sub/c.png", "sub/deeper/d.mp3", "corrupt.pdf"):
        (folder / name).write_bytes(b"data")
    for name in ("notes.xyz", "sub/tool.exe", "noext"):
        (folder / name).write_bytes(b"data")

    processed = []

    def fake_process(path, platform="local", temp_dir=None, **kwargs):
        processed.append(Path(path).name)
        assert temp_dir is not None
        if Path(path).name == "corrupt.pdf":
            raise ValueError("PDF is damaged")

    monkeypatch.setattr(upload_service, "process_uploaded_file", fake_process)
    monkeypatch.setattr(index_manager, "remove_deleted_files", lambda: None)

    assert client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=user["headers"]).status_code == 200

    from app.platforms.local.local_platform import LocalPlatform

    enqueue(client, user, ["local"])
    drain(make_worker(local=LocalPlatform))

    job = jobs_of(client, user)["local"]
    assert sorted(processed) == ["a.pdf", "b.txt", "c.png", "corrupt.pdf", "d.mp3"]
    # 3 unsupported files + 2 sub-folders are skipped, not part of progress.
    assert (job["total_files"], job["skipped_files"]) == (5, 5)
    assert (job["succeeded_files"], job["failed_files"], job["progress"]) == (4, 1, 100)
    assert job["status"] == "completed_with_errors"

    errors = client.get(f"/index/jobs/{job['id']}/errors", headers=user["headers"]).json()["errors"]
    assert len(errors) == 1
    assert errors[0]["file"].endswith("corrupt.pdf")
    assert errors[0]["error"] == "ValueError: PDF is damaged"


def test_local_platform_without_folders_fails(client, user):

    from app.platforms.local.local_platform import LocalPlatform

    enqueue(client, user, ["local"])
    drain(make_worker(local=LocalPlatform))

    job = jobs_of(client, user)["local"]
    assert (job["status"], job["error_message"]) == (
        "failed", "PlatformPreconditionError: No valid local folders are registered."
    )


# ---------------------------------------------------------------------------
# JobContext throttling
# ---------------------------------------------------------------------------

def test_progress_writes_are_throttled(client, user, monkeypatch):

    from app.scheduler.context import JobContext

    flushes = []
    original = JobContext.flush

    def counting_flush(self):
        flushes.append(self.processed_files)
        original(self)

    monkeypatch.setattr(JobContext, "flush", counting_flush)

    enqueue(client, user, ["local"])
    drain(make_worker(local=lambda: FakePlatform(files=[f"{i}.txt" for i in range(35)])))

    # set_total + every 10 files + final forced report + finalize (fast run,
    # so the 1 s timer never fires): far fewer than one write per file.
    assert len(flushes) <= 8
    assert flushes[-1] == 35
    assert jobs_of(client, user)["local"]["processed_files"] == 35


def test_progress_flushes_after_one_second(user):

    from app.scheduler.context import JobContext

    now = [0.0]
    job_id = uuid.uuid4()

    from app.database.db import SessionLocal
    with SessionLocal() as session:
        session.add(IndexingJob(id=job_id, user_id=user["id"], platform="local", status="running"))
        session.commit()

    ctx = JobContext(job_id, user["id"], "local", Path("unused"), clock=lambda: now[0])

    ctx.file_succeeded()
    with SessionLocal() as session:
        assert session.get(IndexingJob, job_id).processed_files == 0

    now[0] = 1.5
    ctx.file_succeeded()
    with SessionLocal() as session:
        stored = session.get(IndexingJob, job_id)
        assert stored.processed_files == 2
        assert stored.heartbeat_at is not None
        stored.status = "cancelled"
        session.commit()
