"""Interim result guard for /search/ (SEC-03; full fix in Phase 3)."""

import uuid

import pytest


@pytest.fixture
def fake_results(monkeypatch, local_root):

    import app.routes.search as search_route

    folder_a = local_root / f"alice-{uuid.uuid4().hex[:6]}"
    folder_a.mkdir()
    (folder_a / "a.pdf").write_text("x")

    results = [
        {"platform": "local", "type": "document", "file": "a.pdf", "path": str(folder_a / "a.pdf")},
        {"platform": "local", "type": "document", "file": "x.pdf", "path": str(local_root / "elsewhere" / "x.pdf")},
        {"platform": "local", "type": "document", "file": "t.pdf", "path": str(folder_a) + "/../escape.pdf"},
        {"platform": "local", "type": "image", "file": "rel.png", "path": "data/rel.png"},
        {"platform": "google_drive", "type": "document", "file": "d.docx", "path": "temp/d.docx", "file_id": "D1"},
        {"platform": "github", "type": "document", "file": "README.md", "path": "README.md", "file_id": "README.md"},
        {"platform": "dropbox", "type": "document", "file": "z", "path": "z"},
    ]

    calls = []

    def fake_search(query, platform="all", search_type="all"):
        calls.append((query, platform, search_type))
        return [dict(r) for r in results]

    monkeypatch.setattr(search_route, "search", fake_search)

    return folder_a, calls


def search(client, user):

    response = client.post("/search/", json={"query": "java"}, headers=user["headers"])
    assert response.status_code == 200
    return response.json()["results"]


def test_user_without_folders_or_connections_sees_nothing(client, user, fake_results):

    assert search(client, user) == []


def test_user_b_cannot_see_user_a_local_results(client, make_user, fake_results):

    folder_a, _ = fake_results
    alice, bob = make_user(), make_user()

    client.post("/platforms/local/folders", json={"folder": str(folder_a)}, headers=alice["headers"])

    alice_files = [r["file"] for r in search(client, alice)]
    assert alice_files == ["a.pdf"]

    assert search(client, bob) == []


def test_cloud_results_require_a_connection(client, user, db, fake_results):

    from app.database.platform_connection_service import disconnect_platform, save_platform_connection

    save_platform_connection(db, user["id"], "google_drive", access_token="t")
    assert [r["platform"] for r in search(client, user)] == ["google_drive"]

    save_platform_connection(db, user["id"], "github", access_token="t")
    assert sorted(r["platform"] for r in search(client, user)) == ["github", "google_drive"]

    disconnect_platform(db, user["id"], "google_drive")
    assert [r["platform"] for r in search(client, user)] == ["github"]


def test_search_passes_parameters_through(client, user, fake_results):

    _, calls = fake_results

    client.post(
        "/search/",
        json={"query": "q", "platform": "local", "search_type": "image"},
        headers=user["headers"]
    )

    assert calls[-1] == ("q", "local", "image")
