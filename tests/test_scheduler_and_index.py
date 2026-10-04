import pytest


@pytest.fixture(autouse=True)
def no_worker(monkeypatch):
    """Never start the real indexing worker in tests."""

    import app.routes.index as index_route
    import app.routes.scheduler as scheduler_route

    started = []

    monkeypatch.setattr(index_route, "start_worker", lambda: started.append("index"))
    monkeypatch.setattr(scheduler_route, "start_worker", lambda: started.append("scheduler"))

    yield started

    from app.scheduler.status import reset_status
    reset_status()


@pytest.mark.parametrize("path", ["/index/", "/scheduler/start"])
@pytest.mark.parametrize("body", [
    {"priority_platform": "dropbox", "platforms": ["dropbox"]},
    {"priority_platform": "local", "platforms": ["local", "Local"]},
    {"priority_platform": "local", "platforms": []},
])
def test_platform_names_are_validated(client, user, path, body, no_worker):

    response = client.post(path, json=body, headers=user["headers"])

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert no_worker == []


def test_index_creates_jobs_with_plain_platform_names(client, user, no_worker, db):

    from app.database.models import IndexingJob

    response = client.post(
        "/index/",
        json={"priority_platform": "github", "platforms": ["local", "github", "local"]},
        headers=user["headers"]
    )

    assert response.status_code == 200
    assert response.json()["platforms"] == ["local", "github"]
    assert no_worker == ["index"]

    jobs = db.query(IndexingJob).filter(IndexingJob.user_id == user["id"]).all()
    assert sorted((j.platform, j.status) for j in jobs) == [("github", "indexing"), ("local", "queued")]


def test_scheduler_status_is_only_visible_to_the_queue_owner(client, make_user, no_worker):

    owner, other = make_user(), make_user()

    started = client.post(
        "/scheduler/start",
        json={"priority_platform": "local", "platforms": ["local", "github"]},
        headers=owner["headers"]
    )
    assert started.status_code == 200

    mine = client.get("/scheduler/status", headers=owner["headers"]).json()
    assert mine["priority_platform"] == "local"
    assert mine["queue"] == ["local", "github"]
    assert "user_id" not in mine

    theirs = client.get("/scheduler/status", headers=other["headers"]).json()
    assert theirs == {
        "current_platform": None,
        "completed_platforms": [],
        "queue": [],
        "worker_running": False,
        "priority_platform": None,
        "priority_completed": False
    }


def test_dashboard_requires_auth_and_answers(client, user):

    assert client.get("/dashboard/stats").status_code == 401
    assert client.get("/dashboard/stats", headers=user["headers"]).status_code == 200
