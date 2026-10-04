"""Upload, delete, open and /files/local (SEC-01, SEC-02, SEC-04)."""

import io
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def no_indexing(monkeypatch):
    """Uploads must not trigger real indexing, and deletes must not touch pickles."""

    import app.routes.upload as upload_route
    import app.services.delete_service as delete_service

    indexed, pruned = [], []

    monkeypatch.setattr(upload_route, "process_uploaded_file", lambda path, *a, **k: indexed.append(path))
    monkeypatch.setattr(delete_service, "remove_from_index", lambda index, name: pruned.append((index, name)))

    return indexed, pruned


def upload(client, user, name="doc.txt", content=b"hello"):

    return client.post(
        "/upload/",
        files={"file": (name, io.BytesIO(content), "application/octet-stream")},
        headers=user["headers"]
    )


def upload_dir(user) -> Path:

    return Path(settings.DATA_DIR) / "uploads" / user["id"]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def test_upload_stores_in_user_dir_and_queues_indexing(client, user, no_indexing):

    response = upload(client, user, "notes.txt", b"abc")

    assert response.status_code == 200
    assert response.json()["filename"] == "notes.txt"
    assert "path" not in response.json()

    stored = upload_dir(user) / "notes.txt"
    assert stored.read_bytes() == b"abc"
    assert no_indexing[0] == [str(stored)]


def test_duplicate_names_get_numeric_suffix(client, user):

    names = [upload(client, user, "same.txt").json()["filename"] for _ in range(3)]

    assert names == ["same.txt", "same (1).txt", "same (2).txt"]


@pytest.mark.parametrize("name", [
    "../evil.txt", "..\\evil.txt", "sub/evil.txt", "sub\\evil.txt",
    "%2e%2e%2fevil.txt", "C:evil.txt", "..",
])
def test_upload_rejects_path_tricks(client, user, name):

    response = upload(client, user, name)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid file name.", "code": "bad_request"}

    assert not (Path(settings.DATA_DIR) / "uploads" / "evil.txt").exists()
    assert not (Path(settings.DATA_DIR) / "evil.txt").exists()


@pytest.mark.parametrize("name", ["run.exe", "script.bat", "noext", "archive.zip"])
def test_upload_rejects_disallowed_extensions(client, user, name):

    response = upload(client, user, name)

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"


def test_upload_rejects_files_over_the_limit(client, user):

    too_big = b"x" * (settings.max_upload_bytes + 1)

    response = upload(client, user, "big.txt", too_big)

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"
    assert not (upload_dir(user) / "big.txt").exists()
    assert not list(upload_dir(user).glob("*.part")) if upload_dir(user).exists() else True


def test_upload_requires_auth(client):

    response = client.post("/upload/", files={"file": ("a.txt", io.BytesIO(b"x"))})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_own_upload(client, user, no_indexing):

    upload(client, user, "gone.txt")

    response = client.delete("/delete/gone.txt", headers=user["headers"])

    assert response.status_code == 200
    assert not (upload_dir(user) / "gone.txt").exists()
    assert ("index.pkl", "gone.txt") in no_indexing[1]


def test_delete_other_users_file_is_404(client, make_user):

    alice, bob = make_user(), make_user()
    upload(client, alice, "private.txt")

    response = client.delete("/delete/private.txt", headers=bob["headers"])

    assert response.status_code == 404
    assert (upload_dir(alice) / "private.txt").exists()


@pytest.mark.parametrize("attack", [
    "..%2F..%2Fsecret.txt",
    "..%5C..%5Csecret.txt",
    "%2E%2E%2F%2E%2E%2Fsecret.txt",
    "C:%5CWindows%5Cwin.ini",
])
def test_delete_traversal_is_404(client, user, attack):

    secret = Path(settings.DATA_DIR) / "secret.txt"
    secret.write_text("keep me")

    upload(client, user, "mine.txt")

    response = client.delete(f"/delete/{attack}", headers=user["headers"])

    assert response.status_code == 404
    assert secret.exists()


def test_delete_missing_is_404(client, user):

    assert client.delete("/delete/nothing.txt", headers=user["headers"]).status_code == 404


# ---------------------------------------------------------------------------
# /files/local and /open/
# ---------------------------------------------------------------------------

@pytest.fixture
def folder(local_root):

    path = local_root / f"docs-{uuid.uuid4().hex[:8]}"
    path.mkdir()
    (path / "report.txt").write_text("report body")

    return path


def register_folder(client, user, path):

    response = client.post("/platforms/local/folders", json={"folder": str(path)}, headers=user["headers"])
    assert response.status_code == 200, response.text


def test_files_local_serves_files_in_registered_folders(client, user, folder):

    register_folder(client, user, folder)

    response = client.get("/files/local", params={"path": str(folder / "report.txt")}, headers=user["headers"])

    assert response.status_code == 200
    assert response.content == b"report body"
    assert "attachment" in response.headers["content-disposition"]


def test_files_local_serves_own_uploads(client, user):

    upload(client, user, "up.txt", b"uploaded")

    response = client.get("/files/local", params={"path": str(upload_dir(user) / "up.txt")}, headers=user["headers"])

    assert response.status_code == 200
    assert response.content == b"uploaded"


def test_files_local_outside_users_folders_is_404(client, make_user, folder, local_root):

    owner, other = make_user(), make_user()
    register_folder(client, owner, folder)
    upload(client, owner, "owner.txt")

    outside = local_root / "loose.txt"
    outside.write_text("not registered")

    for path in (
        folder / "report.txt",                     # someone else's folder
        upload_dir(owner) / "owner.txt",           # someone else's upload
        outside,                                   # not registered by anyone
        Path(settings.DATA_DIR) / "uploads",       # a directory
        folder / ".." / "loose.txt",               # traversal
    ):
        response = client.get("/files/local", params={"path": str(path)}, headers=other["headers"])
        assert response.status_code == 404, path
        assert response.json() == {"detail": "File not found.", "code": "not_found"}


def test_open_local_returns_download_url(client, user, folder):

    register_folder(client, user, folder)

    response = client.post(
        "/open/",
        json={"platform": "local", "path": str(folder / "report.txt")},
        headers=user["headers"]
    )

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "download"
    assert body["filename"] == "report.txt"

    url = urlparse(body["url"])
    assert url.path == "/files/local"

    download = client.get(body["url"], headers=user["headers"])
    assert download.status_code == 200
    assert download.content == b"report body"
    assert Path(parse_qs(url.query)["path"][0]) == (folder / "report.txt").resolve()


def test_open_errors_use_http_status_codes(client, user, local_root):

    outside = local_root / "x.txt"
    outside.write_text("x")

    not_owned = client.post("/open/", json={"platform": "local", "path": str(outside)}, headers=user["headers"])
    assert not_owned.status_code == 404

    unknown = client.post("/open/", json={"platform": "dropbox", "path": "x"}, headers=user["headers"])
    assert unknown.status_code == 400

    drive_not_connected = client.post(
        "/open/", json={"platform": "google_drive", "path": "x", "file_id": "abc"}, headers=user["headers"]
    )
    assert drive_not_connected.status_code == 404


def test_open_drive_returns_url_when_connected(client, user, db):

    from app.database.platform_connection_service import save_platform_connection

    save_platform_connection(db, user["id"], "google_drive", access_token="t", token_json="{}")

    response = client.post(
        "/open/", json={"platform": "google_drive", "path": "x", "file_id": "FILE123"}, headers=user["headers"]
    )

    assert response.status_code == 200
    assert response.json() == {"type": "url", "url": "https://drive.google.com/file/d/FILE123/view"}

    missing_id = client.post("/open/", json={"platform": "google_drive", "path": "x"}, headers=user["headers"])
    assert missing_id.status_code == 400


# ---------------------------------------------------------------------------
# Local folder registration
# ---------------------------------------------------------------------------

def test_folder_must_exist_be_a_dir_and_be_under_allowed_roots(client, user, local_root, tmp_path):

    a_file = local_root / "file.txt"
    a_file.write_text("x")

    elsewhere = tmp_path / "not-allowed"
    elsewhere.mkdir()

    anchor = Path(local_root.anchor)

    cases = {
        str(local_root / "does-not-exist"): "does not exist",
        str(a_file): "not a folder",
        str(anchor): "root",
        str(elsewhere): "outside the allowed",
        "": "required",
    }

    for raw, fragment in cases.items():
        response = client.post("/platforms/local/folders", json={"folder": raw}, headers=user["headers"])
        assert response.status_code == 400, raw
        assert fragment in response.json()["detail"].lower(), (raw, response.json())


def test_folder_is_normalized_and_deduplicated(client, user, folder):

    messy = str(folder) + "/sub/.."
    (folder / "sub").mkdir()

    first = client.post("/platforms/local/folders", json={"folder": messy}, headers=user["headers"])
    second = client.post("/platforms/local/folders", json={"folder": str(folder).replace("\\", "/")}, headers=user["headers"])

    assert first.status_code == second.status_code == 200
    assert second.json()["folders"].count(str(folder.resolve())) == 1

    removed = client.request(
        "DELETE", "/platforms/local/folders", json={"folder": messy}, headers=user["headers"]
    )
    assert removed.status_code == 200
    assert str(folder.resolve()) not in removed.json()["folders"]


def test_unique_constraint_on_user_folder(db, user, folder):

    from sqlalchemy.exc import IntegrityError
    from app.database.models import LocalStorageFolder

    db.add(LocalStorageFolder(user_id=user["id"], folder_path=str(folder)))
    db.add(LocalStorageFolder(user_id=user["id"], folder_path=str(folder)))

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
