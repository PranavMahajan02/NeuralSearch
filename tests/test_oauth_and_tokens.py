"""GitHub OAuth state (SEC-06) and token encryption at rest."""

import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import text

import app.platforms.github.oauth as oauth
from app.core.clock import utcnow
from app.core.config import settings
from app.database.models import OAuthState

FRONTEND = settings.FRONTEND_URL


@pytest.fixture(autouse=True)
def fake_github(monkeypatch):

    import app.routes.github as github_route

    exchanged = []

    def fake_exchange(code):
        exchanged.append(code)
        if code == "bad-code":
            return {"error": "bad_verification_code"}
        if code == "explode":
            raise RuntimeError("<script>alert(1)</script>")
        return {"access_token": "fake-access-token", "token_type": "bearer", "scope": "repo"}

    monkeypatch.setattr(oauth, "load_config", lambda: {"client_id": "cid", "client_secret": "csecret"})
    monkeypatch.setattr(github_route, "exchange_code_for_token", fake_exchange)

    class FakeClient:
        def __init__(self, token, *args, **kwargs):
            pass

        def user(self):
            return {"login": "octocat"}

    # The callback reads the GitHub login; never call the real API in tests.
    monkeypatch.setattr(github_route, "GitHubClient", FakeClient)

    return exchanged


def callback(client, **params):

    return client.get("/platforms/github/callback", params=params, follow_redirects=False)


def redirect_params(response):

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith(FRONTEND + "/?")
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


def start_connect(client, user):

    response = client.get("/platforms/github/connect", headers=user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False

    url = urlparse(body["authorization_url"])
    assert url.netloc == "github.com"
    query = parse_qs(url.query)
    assert query["client_id"] == ["cid"]
    assert query["redirect_uri"] == [f"{settings.BACKEND_PUBLIC_URL}/platforms/github/callback"]

    return query["state"][0]


def test_connect_stores_random_single_use_state(client, user, db):

    state = start_connect(client, user)

    assert len(state) >= 40
    assert state != user["id"]

    row = db.get(OAuthState, state)
    assert str(row.user_id) == user["id"]
    assert row.platform == "github"
    assert row.used is False
    assert timedelta(minutes=9) < row.expires_at - utcnow() <= timedelta(minutes=10)


def test_valid_state_connects_the_state_owner(client, user, db, fake_github):

    state = start_connect(client, user)

    assert redirect_params(callback(client, code="good", state=state)) == {"github": "connected"}
    assert fake_github == ["good"]

    status = client.get("/platforms/github/status", headers=user["headers"])
    assert status.json() == {"connected": True, "account_name": "octocat"}

    db.expire_all()
    assert db.get(OAuthState, state).used is True


def test_missing_state_is_rejected(client, fake_github):

    assert redirect_params(callback(client, code="good")) == {"github": "error", "reason": "missing_state"}
    assert fake_github == []


def test_unknown_state_and_user_uuid_as_state_are_rejected(client, user, fake_github):

    assert redirect_params(callback(client, code="good", state="nope"))["reason"] == "invalid_state"

    # The old CSRF hole: state = victim's user id. Must not be accepted.
    assert redirect_params(callback(client, code="good", state=user["id"]))["reason"] == "invalid_state"

    assert fake_github == []
    assert client.get("/platforms/github/status", headers=user["headers"]).json() == {
        "connected": False,
        "account_name": None,
    }


def test_expired_state_is_rejected(client, user, db, fake_github):

    state = start_connect(client, user)

    row = db.get(OAuthState, state)
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    assert redirect_params(callback(client, code="good", state=state))["reason"] == "state_expired"
    assert fake_github == []


def test_reused_state_is_rejected(client, user, fake_github):

    state = start_connect(client, user)

    assert redirect_params(callback(client, code="good", state=state)) == {"github": "connected"}
    assert redirect_params(callback(client, code="good", state=state))["reason"] == "state_already_used"
    assert fake_github == ["good"]


def test_failed_exchange_redirects_without_reflecting_error_text(client, user):

    for code in ("bad-code", "explode"):
        state = start_connect(client, user)
        response = callback(client, code=code, state=state)
        assert redirect_params(response) == {"github": "error", "reason": "token_exchange_failed"}
        assert "script" not in response.headers["location"]
        assert "script" not in response.text


def test_denied_consent_redirects_with_error(client, user):

    state = start_connect(client, user)

    assert redirect_params(callback(client, error="access_denied", state=state))["reason"] == "access_denied"


# ---------------------------------------------------------------------------
# Token encryption
# ---------------------------------------------------------------------------


def test_crypto_round_trip():

    from app.core.crypto import decrypt, encrypt, is_encrypted

    secret = "gho_example_token_value"
    cipher = encrypt(secret)

    assert cipher != secret
    assert decrypt(cipher) == secret
    assert is_encrypted(cipher)
    assert not is_encrypted(secret)
    # Fernet uses a random IV: same input, different ciphertext.
    assert encrypt(secret) != cipher


def test_platform_tokens_are_ciphertext_in_the_db(user, db):

    from app.database.platform_connection_service import get_platform_connection, save_platform_connection

    save_platform_connection(
        db, user["id"], "github", access_token="plain-access", refresh_token="plain-refresh", token_json='{"k": "v"}'
    )

    raw = db.execute(
        text(
            "SELECT access_token, refresh_token, token_json FROM platform_connections "
            "WHERE user_id = :u AND platform = 'github'"
        ),
        {"u": user["id"]},
    ).one()

    assert all(value.startswith("gAAAAA") for value in raw)
    assert "plain" not in "".join(raw)

    db.expire_all()
    connection = get_platform_connection(db, user["id"], "github")
    assert connection.access_token == "plain-access"
    assert connection.refresh_token == "plain-refresh"
    assert connection.token_json == '{"k": "v"}'


def test_disconnected_github_has_no_usable_token(user, db):

    from app.database.platform_connection_service import disconnect_platform, save_platform_connection

    save_platform_connection(db, user["id"], "github", access_token="tok")
    assert oauth.get_access_token(db, user["id"]) == "tok"

    disconnect_platform(db, user["id"], "github")

    with pytest.raises(Exception, match="not connected"):
        oauth.get_access_token(db, user["id"])

    assert oauth.is_connected(db, user["id"]) is False


def test_encrypt_migration_is_idempotent_and_reversible(user, db):

    from app.core.crypto import is_encrypted

    connection_id = uuid.uuid4()

    # Simulate a legacy plaintext row written before the migration.
    db.execute(
        text(
            "INSERT INTO platform_connections (id, user_id, platform, access_token, connected) "
            "VALUES (:id, :u, 'legacy', 'legacy-plain', true)"
        ),
        {"id": connection_id, "u": user["id"]},
    )
    db.commit()

    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location(
        "m0005", Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0005_encrypt_platform_tokens.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    from app.database.db import engine

    with engine.begin() as conn:

        def read():
            return conn.execute(
                text("SELECT access_token FROM platform_connections WHERE id = :id"), {"id": connection_id}
            ).scalar_one()

        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            first = read()
            migration.upgrade()
            assert read() == first  # idempotent
            assert is_encrypted(first)
            migration.downgrade()
            assert read() == "legacy-plain"  # reversible
            migration.upgrade()  # leave every row encrypted again


def test_token_key_rotation_re_encrypts_every_stored_token(user, db):
    """scripts/rotate_token_key.py: old key -> new key in one transaction, verified."""

    import importlib.util
    from pathlib import Path

    from cryptography.fernet import Fernet

    from app.core.config import settings
    from app.database.db import engine
    from app.database.models import PlatformConnection

    spec = importlib.util.spec_from_file_location(
        "rotate_token_key", Path(__file__).resolve().parent.parent / "scripts" / "rotate_token_key.py"
    )
    rotation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rotation)

    db.add(
        PlatformConnection(
            user_id=user["id"],
            platform="github",
            connected=True,
            access_token="gho_access",
            refresh_token="refresh-1",
            token_json='{"token": "x"}',
        )
    )
    db.commit()
    old_key, new_key = settings.TOKEN_ENCRYPTION_KEY, Fernet.generate_key().decode()

    def raw():
        return db.execute(
            text("SELECT access_token, refresh_token, token_json FROM platform_connections WHERE user_id = :u"),
            {"u": user["id"]},
        ).one()

    before = raw()
    assert rotation.rotate(engine, old_key, new_key, dry_run=True)["values"] >= 3
    db.expire_all()
    assert raw() == before  # dry run writes nothing

    rotation.rotate(engine, old_key, new_key)
    db.expire_all()
    after = raw()
    new = Fernet(new_key.encode())
    assert [new.decrypt(v.encode()).decode() for v in after] == ["gho_access", "refresh-1", '{"token": "x"}']

    # Back to the test key so the rest of the session can read its rows.
    rotation.rotate(engine, new_key, old_key)


def test_rotation_with_a_wrong_old_key_changes_nothing(user, db):

    import importlib.util
    from pathlib import Path

    from cryptography.fernet import Fernet

    from app.database.db import engine
    from app.database.models import PlatformConnection

    spec = importlib.util.spec_from_file_location(
        "rotate_token_key", Path(__file__).resolve().parent.parent / "scripts" / "rotate_token_key.py"
    )
    rotation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rotation)

    db.add(PlatformConnection(user_id=user["id"], platform="google_drive", connected=True, access_token="ya29.x"))
    db.commit()
    before = db.execute(
        text("SELECT access_token FROM platform_connections WHERE user_id = :u"), {"u": user["id"]}
    ).scalar()

    with pytest.raises(SystemExit, match="OLD key"):
        rotation.rotate(engine, Fernet.generate_key().decode(), Fernet.generate_key().decode())

    db.expire_all()
    assert (
        db.execute(text("SELECT access_token FROM platform_connections WHERE user_id = :u"), {"u": user["id"]}).scalar()
        == before
    )
