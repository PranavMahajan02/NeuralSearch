"""Upload, delete, open and /files/local (SEC-01, SEC-02, SEC-04)."""

import io
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def no_indexing(monkeypatch):
    """Uploads queue indexing as a background task; record it instead."""

    import app.routes.upload as upload_route

    indexed = []

    monkeypatch.setattr(
        upload_route, "index_upload_in_background",
        lambda user_id, path: indexed.append((user_id, path))
    )

    return indexed


def index_now(user, path):
    """Index a local file for `user` (fake embedder, in-memory Qdrant)."""

    from app.services.indexing_pipeline import index_local_file

    return index_local_file(user["id"], str(path))


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
    assert no_indexing == [(user["id"], str(stored))]


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

def test_delete_own_upload_removes_file_vectors_and_ledger_row(client, user):

    from app.services import index_store
    from app.services.indexing_pipeline import local_source_id
    from app.vectorstore.client import get_client
    from app.vectorstore.config import collection_for_type
    from app.vectorstore.query import user_filter

    upload(client, user, "gone.txt", b"some searchable words")
    stored = upload_dir(user) / "gone.txt"
    assert index_now(user, stored) == "indexed"
    source_id = local_source_id(str(stored))

    def points():
        return get_client().count(
            collection_for_type("document"),
            count_filter=user_filter(user["id"], "local", source_id=source_id),
            exact=True
        ).count

    assert points() == 1

    response = client.delete("/delete/gone.txt", headers=user["headers"])

    assert response.status_code == 200
    assert not stored.exists()
    assert points() == 0
    assert index_store.get_source(user["id"], "local", source_id) is None


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

    # Registered but not indexed yet: not served.
    not_indexed = client.get("/files/local", params={"path": str(folder / "report.txt")}, headers=user["headers"])
    assert not_indexed.status_code == 404

    index_now(user, folder / "report.txt")

    response = client.get("/files/local", params={"path": str(folder / "report.txt")}, headers=user["headers"])

    assert response.status_code == 200
    assert response.content == b"report body"
    assert "attachment" in response.headers["content-disposition"]


def test_files_local_serves_own_uploads(client, user):

    upload(client, user, "up.txt", b"uploaded")
    index_now(user, upload_dir(user) / "up.txt")

    response = client.get("/files/local", params={"path": str(upload_dir(user) / "up.txt")}, headers=user["headers"])

    assert response.status_code == 200
    assert response.content == b"uploaded"


def test_files_local_outside_users_folders_is_404(client, make_user, folder, local_root):

    owner, other = make_user(), make_user()
    register_folder(client, owner, folder)
    upload(client, owner, "owner.txt")
    index_now(owner, folder / "report.txt")
    index_now(owner, upload_dir(owner) / "owner.txt")

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
    index_now(user, folder / "report.txt")

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


def test_open_drive_returns_url_for_an_indexed_drive_file(client, make_user):

    from app.services import index_store
    from app.services.index_store import FileMeta, IndexPoint

    user, other = make_user(), make_user()

    meta = FileMeta(user_id=user["id"], platform="google_drive", source_id="FILE123",
                    file_name="notes.docx", display_path="notes.docx", file_type="document", version="t1")
    index_store.upsert_file(meta, [IndexPoint(type="document", vector=[1.0] + [0.0] * 383, chunk_index=0, chunk="x")])

    # Someone else's Drive file id: 404.
    not_mine = client.post("/open/", json={"platform": "google_drive", "file_id": "FILE123"}, headers=other["headers"])
    assert not_mine.status_code == 404

    response = client.post(
        "/open/", json={"platform": "google_drive", "path": "x", "file_id": "FILE123"}, headers=user["headers"]
    )

    assert response.status_code == 200
    assert response.json() == {"type": "url", "url": "https://drive.google.com/file/d/FILE123/view"}

    missing_id = client.post("/open/", json={"platform": "google_drive", "path": "x"}, headers=user["headers"])
    assert missing_id.status_code == 404


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


def test_legacy_root_folder_rows_grant_nothing(client, user, db, local_root):
    """A drive/filesystem root stored before validation existed must not make
    every file on the disk downloadable."""

    from app.database.models import LocalStorageFolder

    anchor = Path(local_root.anchor)
    db.add(LocalStorageFolder(user_id=user["id"], folder_path=str(anchor)))
    db.commit()

    loose = local_root / "loose-root-test.txt"
    loose.write_text("x")

    for path in (loose, Path(__file__)):
        response = client.get("/files/local", params={"path": str(path)}, headers=user["headers"])
        assert response.status_code == 404


def test_legacy_folder_outside_allowed_roots_grants_nothing(client, user, db, tmp_path):

    from app.database.models import LocalStorageFolder

    outside = tmp_path / "legacy-outside"
    outside.mkdir()
    (outside / "f.txt").write_text("x")

    db.add(LocalStorageFolder(user_id=user["id"], folder_path=str(outside)))
    db.commit()

    response = client.get("/files/local", params={"path": str(outside / "f.txt")}, headers=user["headers"])
    assert response.status_code == 404
