"""No pickles left, error sanitizing, indexing-pipeline error propagation."""

from pathlib import Path

import pytest

from app.scheduler.errors import sanitize_error


# ---------------------------------------------------------------------------
# The pickle indexes are gone (Phase 3)
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent



def test_no_pickle_anywhere_in_the_app():

    offenders = []

    files = list((ROOT / "app").rglob("*.py"))

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "pickle" in text or ".pkl" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_legacy_index_modules_are_deleted():

    import importlib

    for module in ("app.cache.search_cache", "app.services.index_manager",
                   "app.services.pickle_store", "app.services.index_delete", "clip_utils"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)


# ---------------------------------------------------------------------------
# Error sanitizing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message, expected", [
    ("Bearer abc.def.ghi rejected", "RuntimeError: <redacted> rejected"),
    ("token gho_" + "A" * 30 + " invalid", "RuntimeError: token <redacted> invalid"),
    ("url https://x/y?access_token=secret123&a=1", "RuntimeError: url <url>"),
    ("creds {'refresh_token': '1//abcdef'}", "RuntimeError: creds {'refresh_token': '<redacted>'}"),
    ("open C:\\Users\\other\\private.pdf failed", "RuntimeError: open <path> failed"),
    ("open /home/other/private.pdf failed", "RuntimeError: open <path> failed"),
    ("open \\\\server\\share\\x.pdf failed", "RuntimeError: open <path> failed"),
    ("open C:\\Users\\Jane Doe\\Private Docs\\x.pdf failed", "RuntimeError: open <path> failed"),
    ("see https://example.com/a/b?q=1 for help", "RuntimeError: see <url> for help"),
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
# Indexing pipeline: errors propagate and are recorded
# ---------------------------------------------------------------------------

def test_index_source_reraises_and_records_failed(monkeypatch, user, tmp_path):

    import app.services.indexing_pipeline as pipeline
    from app.services import index_store

    def broken(path, temp_dir=None):
        raise RuntimeError("extractor crashed")

    monkeypatch.setitem(pipeline.BUILDERS, "document", broken)

    file = tmp_path / "a.txt"
    file.write_text("hello")

    with pytest.raises(RuntimeError, match="extractor crashed"):
        pipeline.index_local_file(user["id"], str(file))

    row = index_store.get_source(user["id"], "local", pipeline.local_source_id(str(file)))
    assert (row.status, row.error) == ("failed", "RuntimeError: extractor crashed")

    # A failed file is retried on the next run even with the same version.
    assert index_store.needs_index(user["id"], "local", row.source_id, row.version) is True


def test_upload_background_task_logs_instead_of_raising(monkeypatch, caplog):

    import app.services.indexing_pipeline as pipeline
    import app.services.upload_service as upload_service

    def broken(user_id, path, **kwargs):
        raise RuntimeError("extractor crashed")

    monkeypatch.setattr(pipeline, "index_local_file", broken)

    upload_service.index_upload_in_background("user", "x.pdf")

    assert any("Indexing the uploaded file failed" in r.getMessage() for r in caplog.records)


def test_unsupported_type_is_recorded_not_indexed(user, tmp_path):

    from app.services import index_store
    from app.services.indexing_pipeline import index_local_file, local_source_id

    file = tmp_path / "tool.exe"
    file.write_bytes(b"MZ")

    assert index_local_file(user["id"], str(file)) == "unsupported"
    assert index_store.get_source(user["id"], "local", local_source_id(str(file))).status == "unsupported"


def test_old_scheduler_modules_and_routes_are_gone(app):

    import importlib

    for module in ("app.scheduler.queue", "app.scheduler.status", "app.scheduler.cancel", "app.scheduler.scheduler"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module)

    paths = app.openapi()["paths"]
    assert not any(path.startswith("/scheduler") for path in paths)
    assert "/index/jobs/{job_id}/errors" in paths
    assert "/index/jobs/{job_id}/cancel" in paths
