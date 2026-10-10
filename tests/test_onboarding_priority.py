"""Phase 6B: onboarding flag, "Index next" (prioritize), claim order, exclude globs, purge script."""

import importlib.util
from pathlib import Path

import pytest

from app.database.db import SessionLocal
from app.database.models import IndexedFile
from app.scheduler.jobs import claim_next_job
from app.services import index_store
from app.services.index_store import FileMeta, IndexPoint
from tests.conftest import _bag_of_words_vector
from tests.test_jobs import FakePlatform, drain, enqueue, isolated_queue, jobs_of, make_worker  # noqa: F401

# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


def profile(client, user):

    return client.get("/auth/profile", headers=user["headers"]).json()


@pytest.mark.parametrize("action", ["complete", "skip"])
def test_onboarding_complete_and_skip_set_the_flag(client, user, action):

    assert profile(client, user)["onboarding_completed"] is False

    response = client.post(f"/auth/onboarding/{action}", headers=user["headers"])

    assert response.status_code == 200 and response.json() == {"onboarding_completed": True}
    assert profile(client, user)["onboarding_completed"] is True


def test_onboarding_endpoints_require_auth(client):

    assert client.post("/auth/onboarding/complete").status_code == 401
    assert client.post("/auth/onboarding/skip").status_code == 401


def test_the_flag_is_per_user(client, user, make_user):

    other = make_user()
    client.post("/auth/onboarding/skip", headers=user["headers"])

    assert profile(client, other)["onboarding_completed"] is False


# ---------------------------------------------------------------------------
# Priority: claim order and "Index next"
# ---------------------------------------------------------------------------


def test_the_priority_platform_is_claimed_first_then_creation_order(client, user):

    assert enqueue(client, user, ["local", "google_drive", "github"], priority="github").status_code == 200

    order = []
    with SessionLocal() as db:
        while (job := claim_next_job(db)) is not None:
            order.append(job.platform)
            job.status = "completed"
            db.commit()

    assert order == ["github", "local", "google_drive"]


def test_index_next_moves_a_queued_job_to_the_front(client, user):

    enqueue(client, user, ["local", "google_drive", "github"], priority="local")
    github = jobs_of(client, user)["github"]

    response = client.post(f"/index/jobs/{github['id']}/prioritize", headers=user["headers"])
    assert response.status_code == 200 and response.json()["priority"] == 1

    with SessionLocal() as db:
        assert claim_next_job(db).platform == "github"


def test_index_next_is_owner_only_and_queued_only(client, user, make_user):

    enqueue(client, user, ["local", "github"], priority="local")
    jobs = jobs_of(client, user)
    other = make_user()

    # Another user's job: same answer as a missing one.
    assert client.post(f"/index/jobs/{jobs['github']['id']}/prioritize", headers=other["headers"]).status_code == 404

    # A job that is no longer queued: 409.
    with SessionLocal() as db:
        claimed = claim_next_job(db)
        assert claimed.platform == "local"
    response = client.post(f"/index/jobs/{jobs['local']['id']}/prioritize", headers=user["headers"])
    assert response.status_code == 409 and response.json()["code"] == "job_not_queued"


# ---------------------------------------------------------------------------
# Exclude globs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, excluded",
    [
        ("import_log.txt", True),
        ("server.LOG", True),
        ("project_files.txt", True),
        ("package-lock.json", True),
        ("poetry.lock", True),
        ("app.min.js", True),
        ("bundle.js.map", True),
        ("src/deep/yarn.lock", True),
        ("notes.txt", False),
        ("logbook.md", False),
        ("package.json", False),
        ("my_project_files.txt", False),
    ],
)
def test_default_exclude_globs(name, excluded):

    from app.platforms.indexing import is_excluded

    assert is_excluded(name) is excluded


def test_exclude_globs_are_configurable(monkeypatch):

    from app.core.config import settings
    from app.platforms.indexing import is_excluded

    monkeypatch.setattr(settings, "INDEX_EXCLUDE_GLOBS", "secret_*.txt, *.bak")

    assert is_excluded("secret_plan.txt") and is_excluded("x.BAK")
    assert not is_excluded("import_log.txt")


def test_local_connector_records_glob_matches_as_excluded(client, user, local_root, monkeypatch):

    from app.platforms.local.local_platform import LocalPlatform
    from app.services.indexing_pipeline import local_source_id
    from tests.test_large_files import job_context

    folder = local_root / "glob-test"
    folder.mkdir()
    (folder / "import_log.txt").write_text("generated", encoding="utf-8")
    (folder / "notes.txt").write_text("real notes", encoding="utf-8")

    from unittest.mock import patch

    with patch(
        "app.platforms.local.local_platform.get_local_folders",
        return_value=[type("F", (), {"folder_path": str(folder)})()],
    ):
        LocalPlatform().index(job_context(user, "local"))

    assert (
        index_store.get_source(user["id"], "local", local_source_id(str(folder / "import_log.txt"))).status
        == "excluded"
    )
    assert index_store.get_source(user["id"], "local", local_source_id(str(folder / "notes.txt"))).status == "indexed"


# ---------------------------------------------------------------------------
# scripts/purge_excluded.py
# ---------------------------------------------------------------------------


def load_purge():

    path = Path(__file__).resolve().parent.parent / "scripts" / "purge_excluded.py"
    spec = importlib.util.spec_from_file_location("purge_excluded", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add(user_id, source_id, name):

    meta = FileMeta(
        user_id=user_id,
        platform="github",
        source_id=source_id,
        file_name=name,
        display_path=name,
        file_type="document",
        version="v1",
    )
    index_store.upsert_file(meta, [IndexPoint("document", _bag_of_words_vector(name, 384), 0, name)])


def test_purge_dry_run_changes_nothing_then_purges_only_matches_per_user(user, make_user, capsys):

    other = make_user()
    add(user["id"], "me/r:import_log.txt", "import_log.txt")
    add(user["id"], "me/r:project_files.txt", "project_files.txt")
    add(user["id"], "me/r:train.py", "train.py")
    add(other["id"], "you/r:build.log", "build.log")

    purge = load_purge()

    assert purge.purge(dry_run=True, email=user["email"])["github"] == 2
    with SessionLocal() as db:
        assert db.query(IndexedFile).filter(IndexedFile.user_id == user["id"]).count() == 3

    assert purge.purge(dry_run=False, email=user["email"])["github"] == 2
    with SessionLocal() as db:
        names = {r.file_name for r in db.query(IndexedFile).filter(IndexedFile.user_id == user["id"])}
        assert names == {"train.py"}
        # The other user's file is untouched when purging one user.
        assert db.query(IndexedFile).filter(IndexedFile.user_id == other["id"]).count() == 1

    assert "import_log.txt" not in capsys.readouterr().out  # names only with --show-names
