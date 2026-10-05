"""Drive and GitHub indexing with faked APIs (no network, no models)."""

from pathlib import Path

import pytest

from app.database.models import IndexingJob
from tests.test_jobs import drain, enqueue, isolated_queue, jobs_of, make_worker  # noqa: F401


class HttpErrorLike(Exception):
    """Mimics googleapiclient.errors.HttpError (has .resp.status)."""

    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.resp = type("Resp", (), {"status": status})()


@pytest.fixture
def processed(monkeypatch):

    import app.services.indexing_pipeline as pipeline
    import app.platforms.github.github_platform as github_platform

    seen = []

    def fake_index_source(meta, local_path, temp_dir=None, force=False):
        file_id = meta.source_id if meta.platform == "google_drive" else meta.source_id.split(":", 1)[-1]
        seen.append({"path": Path(local_path), "platform": meta.platform, "temp_dir": temp_dir,
                     "file_id": file_id, "repo": meta.repo, "meta": meta})
        assert Path(local_path).exists()
        if "broken" in Path(local_path).name:
            raise ValueError("could not extract text")
        return "indexed"

    monkeypatch.setattr(pipeline, "index_source", fake_index_source)
    monkeypatch.setattr(github_platform, "index_source", fake_index_source)

    return seen


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

DRIVE_FILES = [
    {"id": "F1", "name": "Folder", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "t"},
    {"id": "D1", "name": "report.pdf", "mimeType": "application/pdf", "modifiedTime": "t1"},
    {"id": "D2", "name": "Meeting notes", "mimeType": "application/vnd.google-apps.document", "modifiedTime": "t2"},
    {"id": "D3", "name": "a/b:c?.txt", "mimeType": "text/plain", "modifiedTime": "t3"},
    {"id": "D4", "name": "broken.docx", "mimeType": "application/msword", "modifiedTime": "t4"},
    {"id": "D5", "name": "archive.zip", "mimeType": "application/zip", "modifiedTime": "t5"},
    {"id": "D6", "name": "Form", "mimeType": "application/vnd.google-apps.form", "modifiedTime": "t6"},
]


@pytest.fixture
def fake_drive(monkeypatch):

    import app.platforms.google_drive.drive_service as drive_service
    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    downloads = []
    fail_auth_on = set()

    def fake_download(user_id, file_id, save_path, mime_type):
        if file_id in fail_auth_on:
            raise HttpErrorLike(401)
        path = Path(save_path)
        if mime_type == "application/vnd.google-apps.document":
            path = path.with_suffix(".docx")
        path.write_bytes(b"content")
        downloads.append(path)
        return str(path)

    monkeypatch.setattr(GoogleDrivePlatform, "list_files", lambda self, user_id: list(DRIVE_FILES))
    monkeypatch.setattr(drive_service, "download_file", fake_download)

    return downloads, fail_auth_on


def test_drive_counts_skips_and_records_per_file_errors(client, user, fake_drive, processed):

    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    downloads, _ = fake_drive

    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=GoogleDrivePlatform))

    job = jobs_of(client, user)["google_drive"]

    # folder + .zip + Google Form are skipped; 4 supported files processed.
    assert (job["total_files"], job["skipped_files"]) == (4, 3)
    assert (job["succeeded_files"], job["failed_files"], job["status"]) == (3, 1, "completed_with_errors")

    names = sorted(item["path"].name for item in processed)
    assert names == ["Meeting notes.docx", "a_b_c_.txt", "broken.docx", "report.pdf"]
    assert {item["file_id"] for item in processed} == {"D1", "D2", "D3", "D4"}

    # Every download lived in this job's own temp dir, one sub-folder per file,
    # and nothing is left behind.
    job_dir = Path(processed[0]["temp_dir"])
    assert job_dir.name == job["id"]
    assert all(path.parent.parent == job_dir for path in downloads)
    assert len({path.parent for path in downloads}) == len(downloads)
    assert not job_dir.exists()

    errors = client.get(f"/index/jobs/{job['id']}/errors", headers=user["headers"]).json()["errors"]
    assert [(e["file"], e["error"]) for e in errors] == [("broken.docx", "ValueError: could not extract text")]


def test_drive_auth_revoked_mid_run_fails_the_job(client, user, fake_drive, processed):

    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    _, fail_auth_on = fake_drive
    fail_auth_on.add("D2")

    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=GoogleDrivePlatform))

    job = jobs_of(client, user)["google_drive"]
    assert job["status"] == "failed"
    assert job["error_message"] == "PlatformPreconditionError: Google Drive access was revoked during indexing."
    assert job["succeeded_files"] == 1


def test_drive_listing_auth_error_is_a_precondition(client, user, monkeypatch):

    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    def denied(self, user_id):
        raise HttpErrorLike(403)

    monkeypatch.setattr(GoogleDrivePlatform, "list_files", denied)

    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=GoogleDrivePlatform))

    job = jobs_of(client, user)["google_drive"]
    assert job["status"] == "failed"
    assert "reconnect Google Drive" in job["error_message"]


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def repo(name):
    return {"name": name, "owner": {"login": "octo"}}


def gh_file(path, sha="s"):
    return {"path": path, "sha": sha, "download_url": f"https://raw.example/{path}"}


@pytest.fixture
def fake_github(monkeypatch):

    import app.platforms.github.github_platform as github_platform

    listings = {
        "app": [gh_file("README.md"), gh_file("src/main.py"), gh_file("logo.png"),
                gh_file("node_modules/x.js"), gh_file("bin/tool.exe"), gh_file("broken.py"),
                {"path": "submodule", "sha": "s", "download_url": None}, gh_file("notes.txt")],
        "docs": [gh_file("README.md"), gh_file("guide.txt"), gh_file("notes.txt")],
    }
    downloads = []

    def fake_list_repos(db, user_id):
        return [repo("app"), repo("empty"), repo("docs")]

    def fake_get_all_files(db, user_id, owner, repo_name):
        if repo_name == "empty":
            raise RuntimeError("409 Client Error: Conflict (repository is empty)")
        return listings[repo_name]

    def fake_download(db, user_id, file_info, download_folder="temp"):
        path = Path(download_folder) / file_info["path"].replace("/", "__")
        path.write_bytes(b"code")
        downloads.append(path)
        return str(path)

    monkeypatch.setattr(github_platform, "list_repositories", fake_list_repos)
    monkeypatch.setattr(github_platform, "get_all_files", fake_get_all_files)
    monkeypatch.setattr(github_platform, "download_file", fake_download)

    return downloads


def test_github_counts_skips_and_isolates_repo_errors(client, user, fake_github, processed):

    from app.platforms.github.github_platform import GitHubPlatform

    enqueue(client, user, ["github"])
    drain(make_worker(github=GitHubPlatform))

    job = jobs_of(client, user)["github"]

    # supported: 2x README.md (Phase 3 added .md), src/main.py, logo.png, broken.py,
    #            app/notes.txt, guide.txt, docs/notes.txt
    # skipped: node_modules/x.js, tool.exe, submodule (no download_url)
    assert (job["total_files"], job["skipped_files"]) == (8, 3)
    assert (job["succeeded_files"], job["failed_files"], job["status"]) == (7, 1, "completed_with_errors")

    # Same path in two repos is processed for each repo.
    notes = [(item["repo"], item["file_id"]) for item in processed if item["file_id"] == "notes.txt"]
    assert sorted(notes) == [("app", "notes.txt"), ("docs", "notes.txt")]

    errors = client.get(f"/index/jobs/{job['id']}/errors", headers=user["headers"]).json()["errors"]
    refs = {e["file"]: e["error"] for e in errors}
    assert refs["octo/empty"].startswith("RuntimeError: 409 Client Error")
    assert refs["octo/app:broken.py"] == "ValueError: could not extract text"

    assert all(not path.exists() for path in fake_github)


def test_github_rate_limit_mid_listing_fails_the_job(client, user, fake_github, processed, monkeypatch):

    import app.platforms.github.github_platform as github_platform
    from app.platforms.errors import PlatformPreconditionError
    from app.platforms.github.github_platform import GitHubPlatform

    def limited(db, user_id, owner, repo_name):
        raise PlatformPreconditionError("GitHub API rate limit exceeded. Try again later.")

    monkeypatch.setattr(github_platform, "get_all_files", limited)

    enqueue(client, user, ["github"])
    drain(make_worker(github=GitHubPlatform))

    job = jobs_of(client, user)["github"]
    assert job["status"] == "failed"
    assert "rate limit" in job["error_message"]
    assert processed == []


def test_github_get_maps_status_codes(monkeypatch, user, db):

    import app.platforms.github.github_service as github_service
    from app.platforms.errors import PlatformPreconditionError

    class Response:
        def __init__(self, status, remaining="10"):
            self.status_code = status
            self.headers = {"X-RateLimit-Remaining": remaining}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    monkeypatch.setattr(github_service, "get_access_token", lambda db, user_id: "token")

    for response, expected in (
        (Response(401), PlatformPreconditionError),
        (Response(403, remaining="0"), PlatformPreconditionError),
        (Response(403), RuntimeError),
        (Response(404), RuntimeError),
    ):
        monkeypatch.setattr(github_service.requests, "get", lambda *a, _r=response, **k: _r)
        with pytest.raises(expected) as error:
            github_service.github_get(db, user["id"], "https://api.github.com/x")
        if response.status_code == 403 and response.headers["X-RateLimit-Remaining"] != "0":
            assert not isinstance(error.value, PlatformPreconditionError)

    monkeypatch.setattr(github_service.requests, "get", lambda *a, **k: Response(200))
    assert github_service.github_get(db, user["id"], "https://api.github.com/x").status_code == 200
