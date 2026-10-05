"""Atomic pickle store, error sanitizing, indexing-chain error propagation."""

import pickle
import threading
import time
from pathlib import Path

import pytest

from app.scheduler.errors import sanitize_error
from app.services.pickle_store import dump_pickle_atomic, load_pickle


# ---------------------------------------------------------------------------
# Atomic pickle writes (BUG-19 / E2)
# ---------------------------------------------------------------------------

def test_concurrent_reader_never_sees_a_partial_pickle(tmp_path):

    path = str(tmp_path / "index.pkl")

    # Two very different payloads; a torn read would fail to unpickle or
    # produce something that is neither.
    small = [{"file": "a", "chunk": "x"}] * 10
    large = [{"file": f"f{i}", "chunk": "y" * 200} for i in range(20000)]

    dump_pickle_atomic(path, small)

    stop = threading.Event()
    problems = []
    reads = [0]

    def writer():
        flip = False
        while not stop.is_set():
            dump_pickle_atomic(path, large if flip else small)
            flip = not flip

    def reader():
        while not stop.is_set():
            try:
                data = load_pickle(path)
            except Exception as error:   # EOFError / UnpicklingError on a torn file
                problems.append(repr(error))
                continue
            if len(data) not in (len(small), len(large)):
                problems.append(f"unexpected length {len(data)}")
            reads[0] += 1

    threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
    for thread in threads:
        thread.start()

    time.sleep(1.5)
    stop.set()
    for thread in threads:
        thread.join()

    assert problems == []
    assert reads[0] > 10
    assert not Path(path + ".tmp").exists()


def test_failed_write_keeps_the_old_file(tmp_path):

    path = str(tmp_path / "index.pkl")
    dump_pickle_atomic(path, [1, 2, 3])

    class Unpicklable:
        def __reduce__(self):
            raise TypeError("cannot pickle this")

    with pytest.raises(TypeError):
        dump_pickle_atomic(path, [Unpicklable()])

    assert load_pickle(path) == [1, 2, 3]


def test_load_missing_pickle_returns_empty(tmp_path):

    assert load_pickle(str(tmp_path / "missing.pkl")) == []


# ---------------------------------------------------------------------------
# Error sanitizing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message, expected", [
    ("Bearer abc.def.ghi rejected", "RuntimeError: <redacted> rejected"),
    ("token gho_" + "A" * 30 + " invalid", "RuntimeError: token <redacted> invalid"),
    ("url https://x/y?access_token=secret123&a=1", "RuntimeError: url https://x/y?access_token=<redacted>&a=1"),
    ("creds {'refresh_token': '1//abcdef'}", "RuntimeError: creds {'refresh_token': '<redacted>'}"),
    ("open C:\\Users\\other\\private.pdf failed", "RuntimeError: open <path> failed"),
    ("open /home/other/private.pdf failed", "RuntimeError: open <path> failed"),
    ("open \\\\server\\share\\x.pdf failed", "RuntimeError: open <path> failed"),
    ("open C:\\Users\\Jane Doe\\Private Docs\\x.pdf failed", "RuntimeError: open <path> failed"),
    ("see https://example.com/a/b for help", "RuntimeError: see https://example.com/a/b for help"),
])
def test_sanitize_error_removes_secrets_and_paths(message, expected):

    assert sanitize_error(RuntimeError(message)) == expected


def test_sanitize_error_keeps_paths_inside_allowed_roots(tmp_path):

    inside = tmp_path / "docs" / "a.pdf"

    text = sanitize_error(ValueError(f"cannot read {inside}"), allowed_roots=[tmp_path])

    assert text == f"ValueError: cannot read {inside}"


def test_sanitize_error_truncates_and_handles_empty_messages():

    assert sanitize_error(KeyError()) == "KeyError"
    assert len(sanitize_error(ValueError("x" * 5000))) == 500


# ---------------------------------------------------------------------------
# Indexing chain no longer swallows errors
# ---------------------------------------------------------------------------

def test_process_uploaded_file_reraises(monkeypatch, tmp_path):

    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "is_file_indexed", lambda *a, **k: False)

    def broken(*args, **kwargs):
        raise RuntimeError("extractor crashed")

    monkeypatch.setattr(upload_service, "index_file", broken)

    with pytest.raises(RuntimeError, match="extractor crashed"):
        upload_service.process_uploaded_file(str(tmp_path / "a.pdf"))


def test_upload_background_task_logs_instead_of_raising(monkeypatch, caplog):

    import app.services.upload_service as upload_service

    def broken(path):
        raise RuntimeError("extractor crashed")

    monkeypatch.setattr(upload_service, "process_uploaded_file", broken)

    upload_service.process_uploaded_file_in_background("x.pdf")

    assert any("Indexing the uploaded file failed" in r.getMessage() for r in caplog.records)


def test_index_file_rejects_unsupported_types():

    from app.services.indexers.index_file import index_file

    with pytest.raises(ValueError, match="Unsupported file type: .exe"):
        index_file("tool.exe")


def test_old_scheduler_modules_and_routes_are_gone(app):

    import importlib

    for module in ("app.scheduler.queue", "app.scheduler.status", "app.scheduler.cancel", "app.scheduler.scheduler"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)

    paths = app.openapi()["paths"]
    assert not any(path.startswith("/scheduler") for path in paths)
    assert "/index/jobs/{job_id}/errors" in paths
    assert "/index/jobs/{job_id}/cancel" in paths
