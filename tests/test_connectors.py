"""Phase 5: GitHub and Google Drive connectors with mocked HTTP / fake clients.

No real Google or GitHub API is ever called: GitHub HTTP goes through the
`responses` mock, Drive uses injected fake clients/services.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from app.database.models import IndexedFile, PlatformConnection
from app.platforms import http
from app.services import index_store
from tests.test_jobs import drain, enqueue, isolated_queue, jobs_of, make_worker  # noqa: F401
from app.core.clock import utcnow


API = "https://api.github.com"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):

    slept = []
    monkeypatch.setattr(http, "sleep", lambda seconds: slept.append(seconds))
    return slept


@pytest.fixture
def mocked():

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


def connect(db, user, platform, token="tok", token_json=None):

    from app.database.platform_connection_service import save_platform_connection

    save_platform_connection(db, user["id"], platform, access_token=token, token_json=token_json)


def ledger(user, platform):

    return {row.source_id: row for row in index_store.list_sources(user["id"], platform)}


def calls_to(mocked, pattern):

    return [c for c in mocked.calls if re.search(pattern, c.request.url)]


# ---------------------------------------------------------------------------
# http helper
# ---------------------------------------------------------------------------

def test_retry_honours_retry_after(mocked, no_sleep):

    mocked.add(responses.GET, "https://x.test/a", status=503, headers={"Retry-After": "2"})
    mocked.add(responses.GET, "https://x.test/a", status=200, json={"ok": True})

    response = http.request("GET", "https://x.test/a")

    assert response.status_code == 200
    assert no_sleep == [2.0]


def test_retry_gives_up_after_max_tries(mocked, no_sleep):

    mocked.add(responses.GET, "https://x.test/b", status=500)

    response = http.request("GET", "https://x.test/b")

    assert response.status_code == 500
    assert len(mocked.calls) == http.MAX_TRIES
    assert len(no_sleep) == http.MAX_TRIES - 1
    assert all(0 <= delay <= http.MAX_DELAY for delay in no_sleep)


def test_connection_errors_are_retried_then_raised(mocked, no_sleep):

    import requests

    mocked.add(responses.GET, "https://x.test/c", body=requests.ConnectionError("down"))

    with pytest.raises(requests.ConnectionError):
        http.request("GET", "https://x.test/c")

    assert len(no_sleep) == http.MAX_TRIES - 1


def test_backoff_grows_exponentially_with_jitter(monkeypatch):

    monkeypatch.setattr(http.random, "uniform", lambda low, high: high)

    assert [http.backoff_delay(n) for n in range(6)] == [1, 2, 4, 8, 16, 30]


def test_call_with_retry_for_client_libraries(no_sleep):

    class HttpErrorLike(Exception):
        def __init__(self, status):
            self.resp = {"status": str(status), "retry-after": "1"}
            self.resp = type("Resp", (dict,), {"status": status})(self.resp)

    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise HttpErrorLike(503)
        return "done"

    from app.platforms.google_drive.drive_service import http_headers, http_status

    assert http.call_with_retry(flaky, http_status, http_headers) == "done"
    assert len(attempts) == 3

    with pytest.raises(HttpErrorLike):
        http.call_with_retry(lambda: (_ for _ in ()).throw(HttpErrorLike(404)), http_status, http_headers)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def gh_repo(name, owner="octo", branch="main", **extra):

    return {"name": name, "owner": {"login": owner}, "default_branch": branch, "fork": False, "archived": False, **extra}


def gh_tree(files):
    """files: {path: (sha, content)}"""

    return {
        "sha": "root",
        "truncated": False,
        "tree": [
            {"path": path, "type": "blob", "sha": sha, "size": len(content)}
            for path, (sha, content) in files.items()
        ],
    }


def mock_repos(mocked, pages):
    """pages: list of lists of repos, served with Link pagination."""

    def callback(request):
        query = parse_qs(urlparse(request.url).query)
        page = int(query.get("page", ["1"])[0])
        headers = {}
        if page < len(pages):
            headers["Link"] = f'<{API}/user/repos?per_page=100&page={page + 1}>; rel="next"'
        return 200, headers, json.dumps(pages[page - 1])

    mocked.add_callback(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), callback=callback)


def mock_repo_files(mocked, owner, repo, files, branch="main"):

    mocked.add(responses.GET, f"{API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1", json=gh_tree(files))

    for path, (sha, content) in files.items():
        mocked.add(responses.GET, f"{API}/repos/{owner}/{repo}/git/blobs/{sha}", body=content)


def run_github(client, user):

    from app.platforms.github.github_platform import GitHubPlatform

    enqueue(client, user, ["github"])
    drain(make_worker(github=GitHubPlatform))

    return jobs_of(client, user)["github"]


@pytest.fixture
def gh_user(user, db):

    connect(db, user, "github")
    return user


def test_github_paginates_repositories_and_indexes_trees(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("a")], [gh_repo("b")], [gh_repo("c")]])
    for name in ("a", "b", "c"):
        mock_repo_files(mocked, "octo", name, {"notes.md": (f"sha-{name}", f"notes for repo {name}")})

    job = run_github(client, gh_user)

    assert job["status"] == "completed"
    assert (job["total_files"], job["succeeded_files"], job["downloaded_files"]) == (3, 3, 3)
    assert len(calls_to(mocked, r"/user/repos")) == 3
    assert set(ledger(gh_user, "github")) == {"octo/a:notes.md", "octo/b:notes.md", "octo/c:notes.md"}


def test_github_second_run_downloads_nothing_and_changed_sha_only_that_file(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("app")]])
    files = {"one.py": ("s1", "print('one')"), "two.py": ("s2", "print('two')")}
    mock_repo_files(mocked, "octo", "app", files)

    assert run_github(client, gh_user)["downloaded_files"] == 2

    second = run_github(client, gh_user)
    assert (second["status"], second["downloaded_files"], second["total_files"], second["skipped_files"]) == ("completed", 0, 0, 2)
    assert len(calls_to(mocked, r"/git/blobs/")) == 2           # no new blob downloads

    # one.py changes on GitHub (new blob sha)
    mocked.replace(responses.GET, f"{API}/repos/octo/app/git/trees/main?recursive=1",
                   json=gh_tree({"one.py": ("s1-new", "print('one v2')"), "two.py": ("s2", "print('two')")}))
    mocked.add(responses.GET, f"{API}/repos/octo/app/git/blobs/s1-new", body="print('one v2')")

    third = run_github(client, gh_user)
    assert third["downloaded_files"] == 1
    assert [c.request.url.rsplit("/", 1)[-1] for c in calls_to(mocked, r"/git/blobs/")][-1] == "s1-new"
    assert ledger(gh_user, "github")["octo/app:one.py"].version == "s1-new"


def test_github_deleted_path_is_removed_from_qdrant_and_ledger(client, gh_user, mocked):

    from tests.test_index_v2 import count_points

    mock_repos(mocked, [[gh_repo("app")]])
    mock_repo_files(mocked, "octo", "app", {"keep.py": ("k", "keep me"), "gone.py": ("g", "delete me")})
    run_github(client, gh_user)
    assert count_points(gh_user["id"], "github", "octo/app:gone.py") == 1

    mocked.replace(responses.GET, f"{API}/repos/octo/app/git/trees/main?recursive=1",
                   json=gh_tree({"keep.py": ("k", "keep me")}))
    run_github(client, gh_user)

    assert set(ledger(gh_user, "github")) == {"octo/app:keep.py"}
    assert count_points(gh_user["id"], "github", "octo/app:gone.py") == 0


def test_github_partial_listing_deletes_nothing(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("app"), gh_repo("broken")]])
    mock_repo_files(mocked, "octo", "app", {"a.py": ("a", "a")})
    mock_repo_files(mocked, "octo", "broken", {"b.py": ("b", "b")})
    run_github(client, gh_user)
    assert len(ledger(gh_user, "github")) == 2

    # The "broken" repo now fails to list: its files must NOT be deleted.
    mocked.replace(responses.GET, f"{API}/repos/octo/broken/git/trees/main?recursive=1", status=500)
    job = run_github(client, gh_user)

    assert job["status"] == "completed"
    assert set(ledger(gh_user, "github")) == {"octo/app:a.py", "octo/broken:b.py"}


def test_github_truncated_tree_falls_back_to_subtrees(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("big")]])
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/trees/main?recursive=1",
               json={"sha": "root", "truncated": True, "tree": []})
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/trees/root",
               json={"tree": [{"path": "top.md", "type": "blob", "sha": "t", "size": 3},
                              {"path": "src", "type": "tree", "sha": "srcsha"}]})
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/trees/srcsha",
               json={"tree": [{"path": "deep.py", "type": "blob", "sha": "d", "size": 4}]})
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/blobs/t", body="top")
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/blobs/d", body="deep")

    run_github(client, gh_user)

    assert set(ledger(gh_user, "github")) == {"octo/big:top.md", "octo/big:src/deep.py"}


def test_github_truncated_tree_with_failing_walk_is_incomplete(client, gh_user, mocked):

    from app.platforms.github.github_service import GitHubClient

    mocked.add(responses.GET, f"{API}/repos/octo/big/git/trees/main?recursive=1",
               json={"sha": "root", "truncated": True, "tree": [{"path": "x.md", "type": "blob", "sha": "x", "size": 1}]})
    mocked.add(responses.GET, f"{API}/repos/octo/big/git/trees/root", status=404)

    entries, complete = GitHubClient("tok").tree("octo", "big", "main")

    assert complete is False
    assert [e.path for e in entries] == ["x.md"]


def test_github_empty_repository_is_zero_files(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("empty")]])
    mocked.add(responses.GET, f"{API}/repos/octo/empty/git/trees/main?recursive=1", status=409,
               json={"message": "Git Repository is empty."})

    job = run_github(client, gh_user)

    assert (job["status"], job["total_files"], job["failed_files"]) == ("completed", 0, 0)


def test_github_open_uses_default_branch(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("app", branch="develop")]])
    mock_repo_files(mocked, "octo", "app", {"docs/read me.md": ("r", "hello world")}, branch="develop")

    run_github(client, gh_user)

    opened = client.post("/open/", json={"platform": "github", "source_id": "octo/app:docs/read me.md"},
                         headers=gh_user["headers"]).json()

    assert opened == {"type": "url", "url": "https://github.com/octo/app/blob/develop/docs/read%20me.md"}
    assert ledger(gh_user, "github")["octo/app:docs/read me.md"].default_branch == "develop"


def test_github_rate_limit_short_wait_then_success(client, gh_user, mocked, no_sleep, monkeypatch):

    monkeypatch.setattr(http, "now", lambda: 1_000_000.0)

    mocked.add(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), status=403,
               headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(1_000_000 + 30)})
    mocked.add(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), json=[])

    job = run_github(client, gh_user)

    assert job["status"] == "completed"
    assert no_sleep == [31.0]


def test_github_rate_limit_long_wait_fails_the_job(client, gh_user, mocked, monkeypatch):

    monkeypatch.setattr(http, "now", lambda: 1_000_000.0)

    mocked.add(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), status=403,
               headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(1_000_000 + 3600)})

    job = run_github(client, gh_user)

    assert job["status"] == "failed"
    assert "rate limited until" in job["error_message"]


def test_github_401_marks_connection_disconnected(client, gh_user, mocked, db):

    mocked.add(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), status=401)

    job = run_github(client, gh_user)

    assert job["status"] == "failed"
    assert "GitHub authorization expired" in job["error_message"]

    db.expire_all()
    connection = db.query(PlatformConnection).filter_by(user_id=gh_user["id"], platform="github").one()
    assert connection.connected is False


def test_github_skips_vendored_paths_and_lfs_pointers(client, gh_user, mocked):

    lfs = "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123456\n"

    mock_repos(mocked, [[gh_repo("app")]])
    mock_repo_files(mocked, "octo", "app", {
        "src/main.py": ("m", "def main(): pass"),
        "node_modules/lib/index.js": ("n", "x"),
        "dist/bundle.js": ("d", "x"),
        "web/app.min.js": ("min", "x"),
        "package-lock.json": ("lock", "{}"),
        "venv/lib/site.py": ("v", "x"),
        "data/model.txt": ("lfs", lfs),
    })

    run_github(client, gh_user)

    rows = ledger(gh_user, "github")
    assert set(rows) == {"octo/app:src/main.py", "octo/app:data/model.txt"}
    assert rows["octo/app:src/main.py"].status == "indexed"
    assert rows["octo/app:data/model.txt"].status == "unsupported"      # LFS pointer, not content
    assert not calls_to(mocked, r"/git/blobs/(n|d|min|lock|v)$")


def test_github_same_path_in_two_repos_are_separate_sources(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("one"), gh_repo("two")]])
    mock_repo_files(mocked, "octo", "one", {"README.md": ("r1", "first readme")})
    mock_repo_files(mocked, "octo", "two", {"README.md": ("r2", "second readme")})

    run_github(client, gh_user)

    rows = ledger(gh_user, "github")
    assert set(rows) == {"octo/one:README.md", "octo/two:README.md"}
    assert {rows[k].version for k in rows} == {"r1", "r2"}


def test_github_skips_forks_and_archived_by_default(client, gh_user, mocked):

    mock_repos(mocked, [[gh_repo("mine"), gh_repo("forked", fork=True), gh_repo("old", archived=True)]])
    mock_repo_files(mocked, "octo", "mine", {"a.md": ("a", "a")})

    run_github(client, gh_user)

    assert set(ledger(gh_user, "github")) == {"octo/mine:a.md"}
    assert not calls_to(mocked, r"/repos/octo/(forked|old)/")


def test_github_too_large_and_unsupported_files_are_recorded_not_downloaded(client, gh_user, mocked, monkeypatch):

    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_DOWNLOAD_MB", 1)

    mock_repos(mocked, [[gh_repo("app")]])
    mocked.add(responses.GET, f"{API}/repos/octo/app/git/trees/main?recursive=1", json={
        "sha": "root", "truncated": False, "tree": [
            {"path": "huge.pdf", "type": "blob", "sha": "h", "size": 5 * 1024 * 1024},
            {"path": "tool.exe", "type": "blob", "sha": "e", "size": 10},
        ]})

    job = run_github(client, gh_user)

    rows = ledger(gh_user, "github")
    assert (rows["octo/app:huge.pdf"].status, rows["octo/app:tool.exe"].status) == ("too_large", "unsupported")
    assert (job["skipped_files"], job["downloaded_files"]) == (2, 0)

    # Recorded with their version: the next run does not reconsider them.
    second = run_github(client, gh_user)
    assert (second["skipped_files"], second["total_files"]) == (2, 0)


def test_github_disconnect_revokes_the_grant(client, gh_user, mocked, monkeypatch, db):

    import app.platforms.github.oauth as oauth

    monkeypatch.setattr(oauth, "load_config", lambda: {"client_id": "cid", "client_secret": "secret"})
    mocked.add(responses.DELETE, f"{API}/applications/cid/grant", status=204)

    body = client.post("/platforms/github/disconnect", headers=gh_user["headers"]).json()

    assert (body["revoked"], body["connected"]) == (True, False)
    revoke = calls_to(mocked, r"/applications/cid/grant")[0]
    assert revoke.request.headers["Authorization"].startswith("Basic ")
    assert json.loads(revoke.request.body) == {"access_token": "tok"}


def test_github_disconnect_still_works_when_revoke_fails(client, gh_user, mocked, monkeypatch, db):

    import app.platforms.github.oauth as oauth

    monkeypatch.setattr(oauth, "load_config", lambda: {"client_id": "cid", "client_secret": "secret"})
    mocked.add(responses.DELETE, f"{API}/applications/cid/grant", status=500)

    body = client.post("/platforms/github/disconnect", headers=gh_user["headers"]).json()

    assert (body["revoked"], body["connected"]) == (False, False)
    assert client.get("/platforms/github/status", headers=gh_user["headers"]).json()["connected"] is False


# ---------------------------------------------------------------------------
# Google Drive: platform with a fake client
# ---------------------------------------------------------------------------

class FakeDrive:

    def __init__(self, files, contents=None, complete=True, fail=()):
        self.files = files
        self.contents = contents or {}
        self.complete = complete
        self.fail = set(fail)
        self.downloads = []
        self.saved = 0

    def list_files(self):
        return list(self.files), self.complete

    def download(self, file, target):
        self.downloads.append(file["id"])
        if file["id"] in self.fail:
            raise RuntimeError("exportSizeLimitExceeded")
        target.write_text(self.contents.get(file["id"], f"content of {file['name']}"), encoding="utf-8")
        return str(target)

    def save_if_refreshed(self):
        self.saved += 1


def d(file_id, name, mime="application/pdf", modified="2026-01-01T00:00:00Z", size=100, **extra):

    return {"id": file_id, "name": name, "mimeType": mime, "modifiedTime": modified,
            "size": str(size) if size is not None else None, "webViewLink": f"https://drive.google.com/file/d/{file_id}/view",
            **extra}


def run_drive(client, user, fake):

    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=lambda: GoogleDrivePlatform(client_factory=lambda user_id: fake)))

    return jobs_of(client, user)["google_drive"]


def test_drive_skips_folders_shortcuts_natives_and_too_large(client, user, monkeypatch):

    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_DOWNLOAD_MB", 1)

    fake = FakeDrive([
        d("F", "Folder", "application/vnd.google-apps.folder", size=None),
        d("S", "Shortcut", "application/vnd.google-apps.shortcut", size=None),
        d("FORM", "Survey", "application/vnd.google-apps.form", size=None),
        d("DOC", "Notes", "application/vnd.google-apps.document", size=None),
        d("SHEET", "Budget", "application/vnd.google-apps.spreadsheet", size=None),
        d("SLIDES", "Deck", "application/vnd.google-apps.presentation", size=None),
        d("BIG", "huge.pdf", size=5 * 1024 * 1024),
        d("ZIP", "archive.zip"),
        d("TXT", "a/b:c?.txt", "text/plain"),
    ])

    job = run_drive(client, user, fake)

    rows = ledger(user, "google_drive")
    assert sorted(fake.downloads) == ["DOC", "SHEET", "SLIDES", "TXT"]
    assert rows["BIG"].status == "too_large" and rows["ZIP"].status == "unsupported"
    assert {rows[k].file_type for k in ("DOC", "SHEET", "SLIDES")} == {"document"}
    assert job["skipped_files"] == 5        # folder, shortcut, form, too large, zip
    assert rows["TXT"].web_view_link == "https://drive.google.com/file/d/TXT/view"
    assert fake.saved == 1


def test_drive_second_run_downloads_nothing_and_modified_file_is_reindexed(client, user):

    files = [d("A", "a.txt", "text/plain"), d("B", "b.txt", "text/plain")]
    fake = FakeDrive(files)

    assert run_drive(client, user, fake)["downloaded_files"] == 2

    fake.downloads.clear()
    second = run_drive(client, user, fake)
    assert (second["downloaded_files"], fake.downloads) == (0, [])

    fake.files = [d("A", "a.txt", "text/plain", modified="2026-02-02T00:00:00Z"), files[1]]
    third = run_drive(client, user, fake)
    assert (third["downloaded_files"], fake.downloads) == (1, ["A"])


def test_drive_md5_change_alone_triggers_reindex(client, user):

    fake = FakeDrive([d("A", "a.txt", "text/plain", md5Checksum="1")])
    run_drive(client, user, fake)

    fake.files = [d("A", "a.txt", "text/plain", md5Checksum="2")]
    fake.downloads.clear()
    run_drive(client, user, fake)

    assert fake.downloads == ["A"]


def test_drive_deleted_file_is_purged_only_on_complete_listing(client, user):

    fake = FakeDrive([d("A", "a.txt", "text/plain"), d("B", "b.txt", "text/plain")])
    run_drive(client, user, fake)

    fake.files = [d("A", "a.txt", "text/plain")]
    fake.complete = False
    run_drive(client, user, fake)
    assert set(ledger(user, "google_drive")) == {"A", "B"}       # partial: nothing deleted

    fake.complete = True
    run_drive(client, user, fake)
    assert set(ledger(user, "google_drive")) == {"A"}


def test_drive_export_failure_is_a_per_file_error(client, user):

    fake = FakeDrive([d("DOC", "Big doc", "application/vnd.google-apps.document", size=None),
                      d("OK", "ok.txt", "text/plain")], fail={"DOC"})

    job = run_drive(client, user, fake)

    assert (job["status"], job["succeeded_files"], job["failed_files"]) == ("completed_with_errors", 1, 1)


def test_drive_temp_names_are_sanitized_and_unique():

    from app.platforms.sync import temp_name

    a = temp_name("id-1", ".pdf")
    assert re.fullmatch(r"[0-9a-f]{20}\.pdf", a)
    assert temp_name("id-2", ".pdf") != a
    assert temp_name("id-3", "/../..\\evil") == temp_name("id-3", "")


# ---------------------------------------------------------------------------
# Google Drive: DriveClient with fake service objects
# ---------------------------------------------------------------------------

class FakeRequest:

    def __init__(self, result):
        self.result = result

    def execute(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeFilesResource:

    def __init__(self, pages):
        self.pages = pages
        self.list_calls = []
        self.exports = []
        self.media = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return FakeRequest(self.pages[len(self.list_calls) - 1])

    def export_media(self, fileId, mimeType):
        self.exports.append((fileId, mimeType))
        return ("export", fileId)

    def get_media(self, fileId):
        self.media.append(fileId)
        return ("media", fileId)


class FakeService:

    def __init__(self, pages=()):
        self.resource = FakeFilesResource(list(pages))

    def files(self):
        return self.resource


class FakeCredentials:

    def __init__(self, token="t1", valid=True, refresh_error=None):
        self.token = token
        self.valid = valid
        self.refresh_token = "r1"
        self.refresh_error = refresh_error

    def refresh(self, request):
        if self.refresh_error:
            raise self.refresh_error
        self.token = "t2-refreshed"
        self.valid = True

    def to_json(self):
        return json.dumps({"token": self.token, "refresh_token": self.refresh_token})


def test_drive_client_paginates(user, db):

    from app.platforms.google_drive.drive_service import DriveClient

    connect(db, user, "google_drive", token_json="{}")

    service = FakeService([
        {"files": [{"id": "1"}], "nextPageToken": "p2"},
        {"files": [{"id": "2"}], "nextPageToken": "p3"},
        {"files": [{"id": "3"}]},
    ])

    files, complete = DriveClient(user["id"], FakeCredentials(), service=service).list_files()

    assert [f["id"] for f in files] == ["1", "2", "3"] and complete is True
    calls = service.resource.list_calls
    assert [c["pageToken"] for c in calls] == [None, "p2", "p3"]
    assert all(c["pageSize"] == 1000 and c["q"] == "trashed=false" for c in calls)
    assert "md5Checksum" in calls[0]["fields"] and "webViewLink" in calls[0]["fields"]


@pytest.mark.parametrize("mime, expected", [
    ("application/vnd.google-apps.document", ("export", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ("application/vnd.google-apps.presentation", ("export", "application/vnd.openxmlformats-officedocument.presentationml.presentation")),
    ("application/vnd.google-apps.spreadsheet", ("export", "text/csv")),
    ("application/pdf", ("media", None)),
])
def test_drive_export_mapping(user, db, tmp_path, monkeypatch, mime, expected):

    import googleapiclient.http as gapi_http
    from app.platforms.google_drive.drive_service import DriveClient

    class FakeDownloader:
        def __init__(self, buffer, request):
            buffer.write(b"bytes")

        def next_chunk(self):
            return None, True

    monkeypatch.setattr(gapi_http, "MediaIoBaseDownload", FakeDownloader)

    service = FakeService()
    drive = DriveClient(user["id"], FakeCredentials(), service=service)

    path = drive.download({"id": "X", "mimeType": mime}, tmp_path / "out")

    assert Path(path).read_bytes() == b"bytes"
    if expected[0] == "export":
        assert service.resource.exports == [("X", expected[1])]
    else:
        assert service.resource.media == ["X"]


def test_drive_refreshed_token_is_persisted_encrypted(user, db):

    from sqlalchemy import text

    from app.core.crypto import decrypt
    from app.platforms.google_drive.drive_service import DriveClient

    connect(db, user, "google_drive", token="t1", token_json=json.dumps({"token": "t1"}))

    creds = FakeCredentials(token="t1", valid=False)
    DriveClient(user["id"], creds, service=FakeService())       # refresh happens on creation

    raw = db.execute(text("SELECT token_json, access_token FROM platform_connections "
                          "WHERE user_id = :u AND platform = 'google_drive'"), {"u": user["id"]}).one()

    assert raw.token_json.startswith("gAAAAA") and "t2-refreshed" not in raw.token_json
    assert json.loads(decrypt(raw.token_json))["token"] == "t2-refreshed"
    assert decrypt(raw.access_token) == "t2-refreshed"


def test_drive_invalid_grant_disconnects_and_fails(client, user, db):

    from google.auth.exceptions import RefreshError

    from app.platforms.google_drive.drive_service import DriveClient, GoogleAuthExpired
    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    connect(db, user, "google_drive", token_json="{}")

    def factory(user_id):
        return DriveClient(user_id, FakeCredentials(valid=False, refresh_error=RefreshError("invalid_grant: Token has been expired or revoked.")),
                           service=FakeService())

    with pytest.raises(GoogleAuthExpired):
        factory(user["id"])

    connect(db, user, "google_drive", token_json="{}")
    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=lambda: GoogleDrivePlatform(client_factory=factory)))

    job = jobs_of(client, user)["google_drive"]
    assert job["status"] == "failed"
    assert "Google authorization expired" in job["error_message"]

    db.expire_all()
    assert db.query(PlatformConnection).filter_by(user_id=user["id"], platform="google_drive").one().connected is False


# ---------------------------------------------------------------------------
# Google Drive: web OAuth
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_google(monkeypatch):

    import app.routes.google_drive as route
    from app.platforms.google_drive import oauth as google_oauth

    exchanged = []

    class FakeFlow:
        code_verifier = "verifier-123"

        def authorization_url(self, **kwargs):
            exchanged.append(("authorize", kwargs))
            return f"https://accounts.google.com/o/oauth2/auth?state={kwargs['state']}", kwargs["state"]

    class Creds:
        token = "access"
        refresh_token = "refresh"
        granted_scopes = ["https://www.googleapis.com/auth/drive.readonly", "openid",
                          "https://www.googleapis.com/auth/userinfo.email"]

        def to_json(self):
            return json.dumps({"token": "access", "refresh_token": "refresh"})

    def fake_exchange(code, verifier):
        exchanged.append(("exchange", code, verifier))
        if code == "bad":
            raise RuntimeError("invalid_grant")
        return Creds()

    monkeypatch.setattr(google_oauth, "build_flow", lambda code_verifier=None: FakeFlow())
    monkeypatch.setattr(google_oauth, "exchange_code", fake_exchange)
    monkeypatch.setattr(google_oauth, "account_email", lambda creds: "owner@example.com")
    monkeypatch.setattr(route, "revoke_token", lambda token: exchanged.append(("revoke", token)) or True)

    return exchanged


def drive_callback(client, **params):

    return client.get("/platforms/google-drive/callback", params=params, follow_redirects=False)


def redirect_params(response):

    from app.core.config import settings

    assert response.status_code == 303
    assert response.headers["location"].startswith(settings.FRONTEND_URL + "/?")
    return {k: v[0] for k, v in parse_qs(urlparse(response.headers["location"]).query).items()}


def test_drive_connect_returns_authorization_url_with_offline_consent(client, user, fake_google, db):

    from app.database.models import OAuthState

    body = client.get("/platforms/google-drive/connect", headers=user["headers"]).json()

    assert body["connected"] is False
    state = parse_qs(urlparse(body["authorization_url"]).query)["state"][0]
    kwargs = fake_google[0][1]
    assert (kwargs["access_type"], kwargs["prompt"], kwargs["include_granted_scopes"]) == ("offline", "consent", "true")

    row = db.get(OAuthState, state)
    assert (row.platform, str(row.user_id), row.code_verifier) == ("google_drive", user["id"], "verifier-123")


def test_drive_callback_valid_state_saves_encrypted_credentials(client, user, fake_google, db):

    from sqlalchemy import text

    state = parse_qs(urlparse(client.get("/platforms/google-drive/connect", headers=user["headers"])
                              .json()["authorization_url"]).query)["state"][0]

    assert redirect_params(drive_callback(client, code="good", state=state)) == {"google_drive": "connected"}
    assert ("exchange", "good", "verifier-123") in fake_google          # PKCE verifier from the DB row

    status = client.get("/platforms/google-drive/status", headers=user["headers"]).json()
    assert status == {"connected": True, "account_email": "owner@example.com"}

    raw = db.execute(text("SELECT token_json FROM platform_connections WHERE user_id = :u AND platform = 'google_drive'"),
                     {"u": user["id"]}).scalar_one()
    assert raw.startswith("gAAAAA") and "refresh" not in raw

    # Reusing the same state is rejected.
    assert redirect_params(drive_callback(client, code="good", state=state))["reason"] == "state_already_used"


@pytest.mark.parametrize("params, reason", [
    ({"code": "good"}, "missing_state"),
    ({"code": "good", "state": "nope"}, "invalid_state"),
])
def test_drive_callback_rejects_bad_states(client, fake_google, params, reason):

    assert redirect_params(drive_callback(client, **params)) == {"google_drive": "error", "reason": reason}
    assert not [e for e in fake_google if e[0] == "exchange"]


def test_drive_callback_expired_state_and_failed_exchange(client, user, fake_google, db):

    from datetime import datetime, timedelta

    from app.database.models import OAuthState

    def new_state():
        body = client.get("/platforms/google-drive/connect", headers=user["headers"]).json()
        return parse_qs(urlparse(body["authorization_url"]).query)["state"][0]

    expired = new_state()
    db.get(OAuthState, expired).expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert redirect_params(drive_callback(client, code="good", state=expired))["reason"] == "state_expired"

    assert redirect_params(drive_callback(client, code="bad", state=new_state()))["reason"] == "token_exchange_failed"
    assert redirect_params(drive_callback(client, error="access_denied", state=new_state()))["reason"] == "access_denied"


def test_drive_disconnect_revokes_and_can_purge(client, user, fake_google, db):

    from app.services.index_store import FileMeta, IndexPoint

    connect(db, user, "google_drive", token="access", token_json="{}")
    meta = FileMeta(user_id=user["id"], platform="google_drive", source_id="D1", file_name="a.txt",
                    display_path="a.txt", file_type="document", version="v")
    index_store.upsert_file(meta, [IndexPoint("document", [1.0] + [0.0] * 383, 0, "x")])

    body = client.post("/platforms/google-drive/disconnect?purge=true", headers=user["headers"]).json()

    assert (body["revoked"], body["connected"], body["purged_files"]) == (True, False, 1)
    assert ("revoke", "access") in fake_google
    assert ledger(user, "google_drive") == {}


def test_drive_open_uses_stored_web_view_link(client, user):

    from app.services.index_store import FileMeta, IndexPoint

    meta = FileMeta(user_id=user["id"], platform="google_drive", source_id="DOC1", file_name="Notes",
                    display_path="Notes", file_type="document", version="v",
                    web_view_link="https://docs.google.com/document/d/DOC1/edit")
    index_store.upsert_file(meta, [IndexPoint("document", [1.0] + [0.0] * 383, 0, "x")])

    opened = client.post("/open/", json={"platform": "google_drive", "source_id": "DOC1"}, headers=user["headers"]).json()

    assert opened == {"type": "url", "url": "https://docs.google.com/document/d/DOC1/edit"}


# ---------------------------------------------------------------------------
# Scanned / image-heavy PDFs (OCR fallback)
# ---------------------------------------------------------------------------

def make_image_pdf(path: Path, pages: int = 1, text_layer: str = None, image_fraction: float = 1.0):
    """A PDF whose pages are images (optionally with a small text layer)."""

    from PIL import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    image = Image.new("RGB", (400, 300), "white")
    width, height = A4

    pdf = canvas.Canvas(str(path), pagesize=A4)
    for _ in range(pages):
        pdf.drawImage(ImageReader(image), 0, 0, width=width, height=height * image_fraction)
        if text_layer:
            pdf.drawString(40, height - 40, text_layer)
        pdf.showPage()
    pdf.save()

    return path


@pytest.fixture
def fake_ocr(monkeypatch):

    import app.extractors.pdf_extract as pdf_extract

    calls = []

    def render(pdf_path, numbers, output_dir):
        calls.extend(numbers)
        return {n: f"page-{n}.jpg" for n in numbers}

    monkeypatch.setattr(pdf_extract, "render_pages", render)
    monkeypatch.setattr(pdf_extract, "ocr_image", lambda path: "Government of India Aadhaar unique identification")

    return calls


def test_image_only_pdf_is_ocrd(tmp_path, fake_ocr):

    from app.extractors.pdf_extract import extract_text

    text = extract_text(str(make_image_pdf(tmp_path / "scan.pdf", pages=2)))

    assert fake_ocr == [1, 2]
    assert text.count("Aadhaar") == 2


def test_image_heavy_page_with_text_appends_ocr(tmp_path, fake_ocr):

    from app.extractors.pdf_extract import extract_text

    pdf = make_image_pdf(tmp_path / "card.pdf", text_layer="1234 5678 9012 name address date of birth details here",
                         image_fraction=0.6)

    text = extract_text(str(pdf))

    assert "1234 5678 9012" in text and "Aadhaar" in text
    assert fake_ocr == [1]


def test_text_pdf_is_not_ocrd(tmp_path, fake_ocr):

    from reportlab.pdfgen import canvas

    from app.extractors.pdf_extract import extract_text

    path = tmp_path / "text.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(40, 800, "A normal document with plenty of real words to read and index properly.")
    pdf.save()

    assert "normal document" in extract_text(str(path))
    assert fake_ocr == []


def test_ocr_is_limited_to_max_pages(tmp_path, fake_ocr, monkeypatch):

    from app.core.config import settings
    from app.extractors.pdf_extract import extract_text

    monkeypatch.setattr(settings, "OCR_MAX_PAGES", 2)

    extract_text(str(make_image_pdf(tmp_path / "long.pdf", pages=5)))

    assert fake_ocr == [1, 2]


def test_ocr_failure_falls_back_to_text_layer(tmp_path, monkeypatch):

    import app.extractors.pdf_extract as pdf_extract

    def broken(*args):
        raise OSError("poppler not found")

    monkeypatch.setattr(pdf_extract, "render_pages", broken)

    text = pdf_extract.extract_text(str(make_image_pdf(tmp_path / "scan.pdf", text_layer="short", pages=3)))

    assert "short" in text


@pytest.mark.parametrize("text, noisy", [
    ("The quick brown fox jumps over the lazy dog again", False),
    ("Xkcd Qwrtp Zxcvb Bnmlk Hjklm Wrtyp Sdfgh Vbnmq", True),
    ("abc", False),
])
def test_noise_detection(text, noisy):

    from app.extractors.pdf_extract import is_noise

    assert is_noise(text) is noisy


def test_scanned_pdf_becomes_searchable_end_to_end(client, user, local_root, fake_ocr):

    folder = local_root / "scans"
    folder.mkdir(exist_ok=True)
    make_image_pdf(folder / "ADHAR.pdf")
    client.post("/platforms/local/folders", json={"folder": str(folder)}, headers=user["headers"])

    from app.services.indexing_pipeline import index_local_file

    assert index_local_file(user["id"], str(folder / "ADHAR.pdf")) == "indexed"

    results = client.post("/search/", json={"query": "aadhaar government"}, headers=user["headers"]).json()["results"]
    assert [r["file"] for r in results] == ["ADHAR.pdf"]


# ---------------------------------------------------------------------------
# Regression: PKCE with the REAL google_auth_oauthlib Flow
# ("invalid_grant: Missing code verifier" during the owner checklist)
# ---------------------------------------------------------------------------

@pytest.fixture
def real_google_client(tmp_path, monkeypatch):
    """A Web-application client config so the real Flow can be built."""

    import app.platforms.google_drive.oauth as google_oauth
    from app.core.config import settings

    secret = tmp_path / "client_secret.json"
    secret.write_text(json.dumps({"web": {
        "client_id": "test-client.apps.googleusercontent.com",
        "client_secret": "test-secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://127.0.0.1:8000/platforms/google-drive/callback"],
    }}))

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET_PATH", str(secret))
    monkeypatch.setattr(google_oauth, "account_email", lambda creds: "owner@example.com")


def pkce_challenge(verifier: str) -> str:

    import base64
    import hashlib

    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def test_real_flow_stores_the_verifier_matching_the_challenge_and_sends_it(client, user, db, mocked, real_google_client):

    from urllib.parse import parse_qs as qs

    from app.database.models import OAuthState

    body = client.get("/platforms/google-drive/connect", headers=user["headers"]).json()
    query = qs(urlparse(body["authorization_url"]).query)

    assert query["code_challenge_method"] == ["S256"]
    challenge = query["code_challenge"][0]
    state = query["state"][0]

    row = db.get(OAuthState, state)
    assert row.code_verifier, "the PKCE verifier must be stored with the state"
    assert 43 <= len(row.code_verifier) <= 128
    assert pkce_challenge(row.code_verifier) == challenge

    mocked.add(responses.POST, "https://oauth2.googleapis.com/token", json={
        "access_token": "ya29.test", "refresh_token": "1//test", "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/drive.readonly openid https://www.googleapis.com/auth/userinfo.email",
    })

    response = client.get("/platforms/google-drive/callback", params={"code": "auth-code", "state": state},
                          follow_redirects=False)

    assert redirect_params(response) == {"google_drive": "connected"}

    token_post = calls_to(mocked, r"oauth2\.googleapis\.com/token")[0]
    sent = qs(token_post.request.body if isinstance(token_post.request.body, str) else token_post.request.body.decode())
    assert sent["code_verifier"] == [row.code_verifier]
    assert sent["code"] == ["auth-code"]

    assert client.get("/platforms/google-drive/status", headers=user["headers"]).json()["connected"] is True


def test_build_flow_has_a_verifier_before_authorization_url(real_google_client):

    from app.platforms.google_drive.oauth import build_flow

    flow = build_flow()
    assert flow.code_verifier and len(flow.code_verifier) >= 43

    # A given verifier is kept as-is (callback side).
    assert build_flow(code_verifier="x" * 50).code_verifier == "x" * 50


def test_callback_with_a_state_missing_its_verifier_is_invalid_state(client, user, db, mocked, real_google_client):

    from app.platforms.oauth_state import create_oauth_state

    state = create_oauth_state(db, user["id"], "google_drive", code_verifier=None)

    response = client.get("/platforms/google-drive/callback", params={"code": "auth-code", "state": state},
                          follow_redirects=False)

    assert redirect_params(response) == {"google_drive": "error", "reason": "invalid_state"}
    assert not calls_to(mocked, r"oauth2\.googleapis\.com/token")



# ---------------------------------------------------------------------------
# Bug #2: Drive scope not granted (granular consent)
# ---------------------------------------------------------------------------

def _token_response(scope: str):

    return {"access_token": "ya29.test", "refresh_token": "1//test", "expires_in": 3600,
            "token_type": "Bearer", "scope": scope}


def _connect_state(client, user):

    from urllib.parse import parse_qs as qs

    body = client.get("/platforms/google-drive/connect", headers=user["headers"]).json()
    return qs(urlparse(body["authorization_url"]).query)["state"][0]


def test_callback_without_drive_scope_saves_nothing_and_revokes(client, user, db, mocked, real_google_client):

    state = _connect_state(client, user)

    mocked.add(responses.POST, "https://oauth2.googleapis.com/token",
               json=_token_response("openid https://www.googleapis.com/auth/userinfo.email"))
    mocked.add(responses.POST, "https://oauth2.googleapis.com/revoke", status=200)

    response = client.get("/platforms/google-drive/callback", params={"code": "c", "state": state},
                          follow_redirects=False)

    assert redirect_params(response) == {"google_drive": "error", "reason": "drive_scope_not_granted"}
    assert calls_to(mocked, r"oauth2\.googleapis\.com/revoke")
    assert db.query(PlatformConnection).filter_by(user_id=user["id"], platform="google_drive").count() == 0
    assert client.get("/platforms/google-drive/status", headers=user["headers"]).json()["connected"] is False


def test_token_json_stores_the_granted_scopes(client, user, db, mocked, real_google_client):

    from app.core.crypto import decrypt
    from sqlalchemy import text

    state = _connect_state(client, user)

    granted = "https://www.googleapis.com/auth/drive.readonly openid https://www.googleapis.com/auth/userinfo.email"
    mocked.add(responses.POST, "https://oauth2.googleapis.com/token", json=_token_response(granted))

    response = client.get("/platforms/google-drive/callback", params={"code": "c", "state": state},
                          follow_redirects=False)
    assert redirect_params(response) == {"google_drive": "connected"}

    raw = db.execute(text("SELECT token_json FROM platform_connections WHERE user_id = :u AND platform = 'google_drive'"),
                     {"u": user["id"]}).scalar_one()

    assert json.loads(decrypt(raw))["scopes"] == sorted(granted.split())


def test_granted_scopes_not_requested_scopes():

    from app.platforms.google_drive.oauth import credentials_json, granted_scopes, has_drive_access

    class Creds:
        scopes = ["https://www.googleapis.com/auth/drive.readonly", "openid", "email"]
        granted_scopes = ["openid", "email"]

        def to_json(self):
            return json.dumps({"token": "t", "scopes": self.scopes})

    assert granted_scopes(Creds()) == ["email", "openid"]
    assert has_drive_access(Creds()) is False
    assert json.loads(credentials_json(Creds()))["scopes"] == ["email", "openid"]


class _HttpError403(Exception):

    def __init__(self, reason):
        super().__init__(f"<HttpError 403 when requesting https://www.googleapis.com/drive/v3/files?q=trashed%3Dfalse "
                         f"returned \"{reason}\">")
        self.resp = type("Resp", (dict,), {"status": 403})({})
        self.content = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()


@pytest.mark.parametrize("reason", ["insufficientPermissions", "insufficientScopes"])
def test_drive_403_permission_fails_job_and_disconnects(client, user, db, reason):

    from app.platforms.google_drive.drive_service import DriveClient
    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform

    connect(db, user, "google_drive", token_json="{}")

    def factory(user_id):
        return DriveClient(user_id, FakeCredentials(), service=FakeService([_HttpError403(reason)]))

    enqueue(client, user, ["google_drive"])
    drain(make_worker(google_drive=lambda: GoogleDrivePlatform(client_factory=factory)))

    job = jobs_of(client, user)["google_drive"]
    assert job["status"] == "failed"
    assert job["error_message"] == ("Google Drive permission missing — "
                                    "reconnect and allow Drive access.")
    assert "http" not in job["error_message"] and "?" not in job["error_message"]

    db.expire_all()
    assert db.query(PlatformConnection).filter_by(user_id=user["id"], platform="google_drive").one().connected is False


def test_github_token_without_repo_scope_fails_and_disconnects(client, gh_user, mocked, db):

    mocked.add(responses.GET, re.compile(re.escape(API) + r"/user/repos.*"), status=403,
               headers={"X-OAuth-Scopes": "read:user", "X-RateLimit-Remaining": "4999"})

    job = run_github(client, gh_user)

    assert job["status"] == "failed"
    assert "GitHub permission missing" in job["error_message"]

    db.expire_all()
    assert db.query(PlatformConnection).filter_by(user_id=gh_user["id"], platform="github").one().connected is False


def test_job_errors_never_contain_urls(client, user):

    class Leaky:
        def index(self, ctx):
            raise RuntimeError("GET https://api.example.com/v1/files?token=abc&page=2 failed")

    enqueue(client, user, ["local"])
    drain(make_worker(local=Leaky))

    message = jobs_of(client, user)["local"]["error_message"]
    assert message == "RuntimeError: GET <url> failed"


def test_pages_render_in_contiguous_runs():

    from app.extractors.pdf_extract import page_runs

    assert page_runs([9, 1, 2, 3, 7, 10]) == [(1, 3), (7, 7), (9, 10)]
    assert page_runs([]) == []


def test_ocr_stops_after_a_failing_page(tmp_path, monkeypatch):

    import app.extractors.pdf_extract as pdf_extract

    calls = []

    def ocr(path):
        calls.append(path)
        raise RuntimeError("paddle crashed")

    monkeypatch.setattr(pdf_extract, "render_pages", lambda pdf, numbers, out: {n: f"p{n}" for n in numbers})
    monkeypatch.setattr(pdf_extract, "ocr_image", ocr)

    text = pdf_extract.extract_text(str(make_image_pdf(tmp_path / "scan.pdf", text_layer="short", pages=3)))

    assert calls == ["p1"] and "short" in text
