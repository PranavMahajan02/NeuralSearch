"""Phase 7A.5: stage timing spans and the per-job "where the time went" totals."""

import contextvars
import threading
import time

from app.core.timing import STAGES, StageTimer, collecting, file_scope, span


def test_spans_record_self_time_so_stages_add_up():

    timer = StageTimer()

    with collecting(timer), file_scope("document"), span("extract_text"):
        time.sleep(0.02)
        with span("ocr"):
            time.sleep(0.05)

    seconds = timer.snapshot()["seconds"]
    assert 0.04 <= seconds["ocr"] < 0.2
    assert 0.01 <= seconds["extract_text"] < 0.05  # excludes the nested OCR
    assert seconds["other"] < 0.01  # file scope minus its stages
    assert timer.snapshot()["by_type"]["document"]["ocr"] == seconds["ocr"]


def test_without_a_timer_spans_are_harmless():

    with span("minilm"):
        pass


def test_snapshot_is_json_ready_and_in_pipeline_order():

    timer = StageTimer()
    for stage in ("ledger", "download", "custom", "minilm"):
        timer.add(stage, 1.23456, "image")

    snap = timer.snapshot()
    assert list(snap["seconds"]) == ["download", "minilm", "ledger", "custom"]
    assert snap["seconds"]["download"] == 1.235 and snap["calls"]["minilm"] == 1
    assert set(STAGES) >= {"download", "ocr", "whisper", "frame_extract", "clip_image", "qdrant_upsert"}


def test_threads_started_with_a_copied_context_report_to_the_same_timer():

    timer = StageTimer()

    def work():
        with file_scope("image"), span("clip_image"):
            time.sleep(0.01)

    with collecting(timer):
        threads = [threading.Thread(target=contextvars.copy_context().run, args=(work,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert timer.snapshot()["calls"]["clip_image"] == 4


def test_a_job_stores_its_stage_timings(client, user, local_root, monkeypatch):

    import uuid

    from tests.test_jobs import drain, enqueue, jobs_of, make_worker

    folder = local_root / f"timed-{uuid.uuid4().hex[:6]}"
    folder.mkdir()
    (folder / "a.txt").write_text("hello world " * 50, encoding="utf-8")
    assert (
        client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=user["headers"]).status_code
        == 200
    )

    from app.platforms.local.local_platform import LocalPlatform

    enqueue(client, user, ["local"])
    drain(make_worker(local=LocalPlatform))

    job = jobs_of(client, user)["local"]
    timings = job["stage_timings"]
    assert job["status"] == "completed"
    assert {"extract_text", "minilm", "qdrant_upsert", "ledger"} <= set(timings["seconds"])
    assert "document" in timings["by_type"]


def test_waiting_for_a_shared_model_is_its_own_stage():

    from app.core.timing import waiting_for

    timer, lock = StageTimer(), threading.Lock()

    def holder():
        with waiting_for(lock):
            time.sleep(0.1)

    with collecting(timer):
        first = threading.Thread(target=contextvars.copy_context().run, args=(holder,))
        first.start()
        time.sleep(0.02)
        with span("minilm"), waiting_for(lock):
            pass
        first.join()

    seconds = timer.snapshot()["seconds"]
    assert seconds["model_wait"] >= 0.05  # the second caller waited for the first
    assert seconds["minilm"] < 0.02  # ... and that wait is not counted as MiniLM time
