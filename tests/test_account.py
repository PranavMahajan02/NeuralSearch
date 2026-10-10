"""Phase 7A-B: user data rights - change password, export, delete account."""

import pytest

from app.core.crypto import encrypt  # noqa: F401  (ensures the Fernet key is configured)
from app.database.db import SessionLocal
from app.database.models import IndexedFile, IndexingJob, LocalStorageFolder, PlatformConnection, User
from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint
from app.vectorstore.client import get_client
from app.vectorstore.config import all_collections
from app.vectorstore.query import user_filter
from tests.conftest import _bag_of_words_vector


def add_file(user, source_id="D-1", name="notes.pdf"):

    meta = FileMeta(
        user_id=user["id"],
        platform="google_drive",
        source_id=source_id,
        file_name=name,
        display_path=name,
        file_type="document",
        version="v1",
    )
    index_store.upsert_file(meta, [IndexPoint("document", _bag_of_words_vector("hello", 384), 0, "hello")])


def points_of(user_id) -> int:

    client = get_client()
    return sum(
        client.count(name, count_filter=user_filter(str(user_id), "all"), exact=True).count
        for name in all_collections()
    )


def add_connection(user, platform="google_drive"):

    with SessionLocal() as db:
        db.add(
            PlatformConnection(
                user_id=user["id"],
                platform=platform,
                connected=True,
                account_email="me@example.com",
                access_token="secret-access",
                refresh_token="secret-refresh",
                token_json='{"token": "secret"}',
            )
        )
        db.commit()


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------


def test_change_password_ends_every_session(client, user):

    other_session = client.post("/auth/login", json={"email": user["email"], "password": user["password"]}).json()
    response = client.post(
        "/auth/change-password",
        headers=user["headers"],
        json={"current_password": user["password"], "new_password": "Brandnew123"},
    )
    assert response.status_code == 200

    for token in (user["token"], other_session["access_token"]):
        assert client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    assert client.post("/auth/login", json={"email": user["email"], "password": user["password"]}).status_code == 401
    assert client.post("/auth/login", json={"email": user["email"], "password": "Brandnew123"}).status_code == 200


def test_change_password_checks_the_current_password_and_the_policy(client, user):

    wrong = client.post(
        "/auth/change-password",
        headers=user["headers"],
        json={"current_password": "nope12345", "new_password": "Brandnew123"},
    )
    assert wrong.status_code == 403  # not 401: the session is still valid

    weak = client.post(
        "/auth/change-password",
        headers=user["headers"],
        json={"current_password": user["password"], "new_password": "short"},
    )
    assert weak.status_code == 422

    assert client.get("/auth/profile", headers=user["headers"]).status_code == 200


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_contains_my_data_and_no_secrets(client, user, make_user):

    add_file(user)
    add_connection(user)
    other = make_user()
    add_file(other, "D-2", "not-mine.pdf")

    response = client.get("/auth/export", headers=user["headers"])
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    data = response.json()
    assert data["profile"]["email"] == user["email"]
    assert [f["file_name"] for f in data["files"]] == ["notes.pdf"]
    assert data["connections"] == [
        {"platform": "google_drive", "account_email": "me@example.com", "account_name": None, "connected": True}
    ]
    assert "secret" not in response.text and "password" not in response.text.lower()
    assert "vector" not in response.text


def test_export_requires_auth(client):

    assert client.get("/auth/export").status_code == 401


# ---------------------------------------------------------------------------
# Delete account
# ---------------------------------------------------------------------------


def test_delete_account_removes_everything_and_revokes_grants(client, user, make_user, monkeypatch, local_root):

    import app.services.account_service as account

    revoked = []
    monkeypatch.setattr(account, "_revokers", lambda: {"google_drive": lambda token: revoked.append(token) or True})

    add_file(user)
    add_connection(user)
    with SessionLocal() as db:
        db.add(LocalStorageFolder(user_id=user["id"], folder_path=str(local_root)))
        db.add(IndexingJob(user_id=user["id"], platform="local", status="completed"))
        db.commit()
    other = make_user()
    add_file(other, "D-9", "theirs.pdf")
    assert points_of(user["id"]) == 1

    response = client.request("DELETE", "/auth/account", headers=user["headers"], json={"password": user["password"]})

    assert response.status_code == 200, response.text
    assert response.json()["deleted_files"] == 1
    assert revoked == ["secret-refresh"]  # the grant is revoked at the provider
    assert client.get("/auth/profile", headers=user["headers"]).status_code == 401  # logged out at once
    assert points_of(user["id"]) == 0
    with SessionLocal() as db:
        for model in (User, IndexedFile, IndexingJob, LocalStorageFolder, PlatformConnection):
            column = model.id if model is User else model.user_id
            assert db.query(model).filter(column == user["id"]).count() == 0
        # The other user is untouched.
        assert db.query(IndexedFile).filter(IndexedFile.user_id == other["id"]).count() == 1
    assert points_of(other["id"]) == 1


def test_delete_account_needs_the_password(client, user):

    response = client.request("DELETE", "/auth/account", headers=user["headers"], json={"password": "wrong-pass1"})

    assert response.status_code == 403
    assert client.get("/auth/profile", headers=user["headers"]).status_code == 200


def test_delete_account_waits_for_a_running_job(client, user):

    with SessionLocal() as db:
        db.add(IndexingJob(user_id=user["id"], platform="local", status="running"))
        db.commit()

    response = client.request("DELETE", "/auth/account", headers=user["headers"], json={"password": user["password"]})

    assert response.status_code == 409
    with SessionLocal() as db:
        job = db.query(IndexingJob).filter(IndexingJob.user_id == user["id"]).one()
        assert job.cancel_requested is True  # asked to stop; the account still exists
        job.status = "cancelled"
        db.commit()

    assert (
        client.request(
            "DELETE", "/auth/account", headers=user["headers"], json={"password": user["password"]}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("email", ["pranav2@gmail.com", " PRANAV2@gmail.com "])
def test_the_admin_script_refuses_the_owner(email):

    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "delete_user.py"
    spec = importlib.util.spec_from_file_location("delete_user", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(SystemExit, match="protected"):
        module.main(email, dry_run=False)
