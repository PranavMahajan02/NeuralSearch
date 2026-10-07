"""scripts/delete_e2e_user.py: only throwaway e2e users, and all their data."""

import importlib.util
from pathlib import Path

import pytest

from app.database.db import SessionLocal
from app.database.models import IndexedFile, User
from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint
from tests.conftest import _bag_of_words_vector


def load_script():

    path = Path(__file__).resolve().parent.parent / "scripts" / "delete_e2e_user.py"
    spec = importlib.util.spec_from_file_location("delete_e2e_user", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("email", ["pranav2@gmail.com", "e2e-x@cogniseek.dev.evil.com", "admin@cogniseek.dev"])
def test_refuses_anything_but_e2e_test_accounts(email):

    with pytest.raises(SystemExit, match="Refusing"):
        load_script().delete_user(email)


def test_deletes_the_test_user_and_all_their_data(client, make_user):

    email = "e2e-abc123@cogniseek.dev"
    response = client.post("/auth/register", json={"name": "E2E", "email": email, "password": "Password123"})
    assert response.status_code == 200, response.text
    user_id = response.json()["id"]
    other = make_user()

    for owner in (user_id, other["id"]):
        meta = FileMeta(user_id=owner, platform="google_drive", source_id=f"D-{owner}", file_name="a.pdf",
                        display_path="a.pdf", file_type="document", version="v1")
        index_store.upsert_file(meta, [IndexPoint("document", _bag_of_words_vector("text", 384), 0, "text")])

    assert load_script().delete_user(email) is True

    with SessionLocal() as db:
        assert db.query(User).filter(User.email == email).count() == 0
        assert db.query(IndexedFile).filter(IndexedFile.user_id == user_id).count() == 0
        # Another user's data is untouched.
        assert db.query(IndexedFile).filter(IndexedFile.user_id == other["id"]).count() == 1

    assert load_script().delete_user(email) is False
