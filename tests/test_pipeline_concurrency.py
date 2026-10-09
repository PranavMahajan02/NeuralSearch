"""Phase 7A.5-B4/B6: the parallel file loop, the shared rate-limit pause and the
smallest-first schedule."""

import threading
import time
from pathlib import Path

import pytest

from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import TYPE_ORDER, process_files, schedule_key


class FakeCtx:
    """The JobContext surface used by process_files / sync_remote."""

    def __init__(self, temp_dir: Path, cancel_after_starts=None):

        self.temp_dir = temp_dir
        self.user_id = "u"
        self.lock = threading.Lock()
        self.started, self.succeeded, self.failed = [], [], []
        self.downloaded = self.skipped = self.total = 0
        self.cancel_after_starts = cancel_after_starts

    def is_cancelled(self):
        with self.lock:
            return self.cancel_after_starts is not None and len(self.started) >= self.cancel_after_starts

    def start_file(self, ref):
        with self.lock:
            self.started.append(ref)

    def file_succeeded(self):
        with self.lock:
            self.succeeded.append(1)

    def file_failed(self, ref, error):
        with self.lock:
            self.failed.append((ref, str(error)))

    def file_downloaded(self):
        with self.lock:
            self.downloaded += 1

    def add_skipped(self, count=1):
        self.skipped += count

    def set_total(self, total):
        self.total = total

    def report_progress(self, force=False):
        pass

    def file_dir(self, index):
        path = self.temp_dir / f"{index:06d}"
        path.mkdir(parents=True, exist_ok=True)
        return path


class Concurrency:
    """Tracks how many handlers run at the same time."""

    def __init__(self):
        self.lock = threading.Lock()
        self.now = self.peak = 0

    def __enter__(self):
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)

    def __exit__(self, *exc):
        with self.lock:
            self.now -= 1


def test_files_run_in_parallel_but_never_more_than_the_workers(tmp_path):

    ctx, live = FakeCtx(tmp_path), Concurrency()

    def handle(position, item):
        with live:
            time.sleep(0.05)

    process_files(ctx, list(range(12)), str, handle, workers=4, prefetch=8)

    assert len(ctx.succeeded) == 12
    assert 2 <= live.peak <= 4


def test_the_in_flight_window_is_bounded(tmp_path):
    """Items are pulled lazily: never more than `prefetch` pulled but unfinished."""

    ctx = FakeCtx(tmp_path)
    lock = threading.Lock()
    finished, worst = [0], [0]

    def handle(position, item):
        time.sleep(0.01)
        with lock:
            finished[0] += 1

    def items():
        for n in range(30):
            with lock:
                worst[0] = max(worst[0], (n + 1) - finished[0])   # this item included
            yield n

    process_files(ctx, items(), str, handle, workers=2, prefetch=3)

    assert len(ctx.succeeded) == 30
    assert worst[0] <= 3


def test_one_failing_file_does_not_stop_the_others(tmp_path):

    ctx = FakeCtx(tmp_path)

    def handle(position, item):
        if item == 3:
            raise ValueError("corrupt file")

    process_files(ctx, list(range(8)), str, handle, workers=4)

    assert len(ctx.succeeded) == 7
    assert ctx.failed == [("3", "corrupt file")]


def test_cancel_stops_starting_files_and_lets_running_ones_finish(tmp_path):

    ctx = FakeCtx(tmp_path, cancel_after_starts=3)
    finished = []

    def handle(position, item):
        time.sleep(0.05)
        finished.append(item)

    process_files(ctx, list(range(20)), str, handle, workers=4, prefetch=4)

    # Cancel is checked before each new file: at most the in-flight window
    # beyond the cancel point, and every started file finished cleanly.
    assert 3 <= len(ctx.started) <= 3 + 4
    assert sorted(finished) == sorted(int(s) for s in ctx.started)
    assert len(ctx.started) < 20


def test_a_precondition_error_aborts_the_job_after_in_flight_files(tmp_path):

    ctx = FakeCtx(tmp_path)

    def handle(position, item):
        if item == 2:
            raise PlatformPreconditionError("Google Drive access was revoked.")
        time.sleep(0.02)

    with pytest.raises(PlatformPreconditionError, match="revoked"):
        process_files(ctx, list(range(50)), str, handle, workers=4, prefetch=4)

    assert len(ctx.started) < 50          # no new files after the abort
    assert ctx.failed == []               # an abort is not a per-file failure


def test_workers_1_is_strictly_sequential(tmp_path):

    ctx, live = FakeCtx(tmp_path), Concurrency()

    def handle(position, item):
        with live:
            time.sleep(0.01)

    process_files(ctx, list(range(5)), str, handle, workers=1)

    assert live.peak == 1 and ctx.started == ["0", "1", "2", "3", "4"]


def test_stage_timings_from_worker_threads_reach_the_job_timer(tmp_path):

    from app.core.timing import StageTimer, collecting, span

    timer = StageTimer()

    def handle(position, item):
        with span("ocr"):
            time.sleep(0.01)

    with collecting(timer):
        process_files(FakeCtx(tmp_path), list(range(6)), str, handle, workers=3)

    assert timer.snapshot()["calls"]["ocr"] == 6


# ---------------------------------------------------------------------------
# Rate limits are shared by parallel downloads
# ---------------------------------------------------------------------------

def test_a_429_seen_by_one_download_pauses_all_parallel_downloads(monkeypatch):

    from app.platforms import http

    clock = {"t": 1000.0}
    slept = []
    lock = threading.Lock()

    def fake_sleep(seconds):
        with lock:
            slept.append(round(seconds, 1))
            clock["t"] += seconds

    monkeypatch.setattr(http, "now", lambda: clock["t"])
    monkeypatch.setattr(http, "sleep", fake_sleep)

    class Response:
        def __init__(self, status, headers=None):
            self.status_code, self.headers = status, headers or {}

    calls = []

    class Session:
        def request(self, method, url, timeout=None, **kwargs):
            with lock:
                calls.append(url)
                first = len(calls) == 1
            return Response(429, {"Retry-After": "7"}) if first else Response(200)

    # The first request is rate limited: the gate is held for 7 s ...
    assert http.request("GET", "https://api.example/1", session=Session()).status_code == 200
    assert slept == [7.0]
    # ... and every request sent during the pause waits it out too.
    http.gate.hold(5)
    results = []
    threads = [threading.Thread(target=lambda n=n: results.append(
        http.request("GET", f"https://api.example/p{n}", session=Session()).status_code)) for n in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [200, 200, 200]
    assert slept.count(5.0) >= 1 and sum(slept) >= 12.0


# ---------------------------------------------------------------------------
# Temp files are deleted per file, also in parallel
# ---------------------------------------------------------------------------

def test_parallel_sync_deletes_every_downloaded_file(tmp_path, monkeypatch):

    from app.platforms import sync
    from app.services.index_store import FileMeta

    monkeypatch.setattr(sync.index_store, "needs_index", lambda *a: True)
    monkeypatch.setattr(sync.index_store, "list_sources", lambda *a: [])
    monkeypatch.setattr(sync.index_store, "delete_sources", lambda *a: 0)
    indexed = []
    monkeypatch.setattr("app.services.indexing_pipeline.index_source",
                        lambda meta, path, **kw: indexed.append(Path(path).read_text()))

    def remote(n):
        meta = FileMeta(user_id="u", platform="google_drive", source_id=f"id{n}", file_name=f"f{n}.txt",
                        display_path=f"f{n}.txt", file_type="document", version="1")

        def download(target):
            target.write_text(f"content {n}")
            return str(target)

        return sync.RemoteFile(meta=meta, extension=".txt", size=10, download=download)

    from app.core.config import settings
    monkeypatch.setattr(settings, "INDEX_IO_WORKERS", 4)
    ctx = FakeCtx(tmp_path)

    result = sync.sync_remote(ctx, "google_drive", [remote(n) for n in range(10)], listing_complete=True)

    assert result.to_index == 10 and ctx.downloaded == 10 and len(indexed) == 10
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def test_small_fast_files_go_first_and_the_order_is_deterministic():

    files = [("video", 50, "v.mp4"), ("document", 900, "big.pdf"), ("image", 5, "a.png"),
             ("audio", 1, "s.mp3"), ("document", 3, "notes.txt"), ("document", 3, "a.txt"), (None, None, "x")]

    ordered = sorted(files, key=lambda f: schedule_key(*f))

    assert [f[2] for f in ordered] == ["a.txt", "notes.txt", "big.pdf", "a.png", "s.mp3", "v.mp4", "x"]
    assert list(TYPE_ORDER) == ["document", "image", "audio", "video"]


def test_local_platform_indexes_in_schedule_order(tmp_path):

    from app.platforms.local.local_platform import local_schedule_key

    (tmp_path / "clip.mp4").write_bytes(b"x" * 10)
    (tmp_path / "photo.jpg").write_bytes(b"x" * 10)
    (tmp_path / "big.pdf").write_bytes(b"x" * 100)
    (tmp_path / "small.txt").write_bytes(b"x")

    paths = sorted((str(p) for p in tmp_path.iterdir()), key=local_schedule_key)

    assert [Path(p).name for p in paths] == ["small.txt", "big.pdf", "photo.jpg", "clip.mp4"]
