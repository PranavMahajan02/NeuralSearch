import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings


def register(client, **overrides):

    body = {"name": "Alice", "email": f"a-{uuid.uuid4().hex[:8]}@example.com", "password": "Password123"}
    body.update(overrides)

    return client.post("/auth/register", json=body)


# ---------------------------------------------------------------------------
# Registration validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"name": "   "}, "Name must be 1-100"),
        ({"name": "x" * 101}, "Name must be 1-100"),
        ({"password": "short1"}, "8-128"),
        ({"password": "a" * 129 + "1"}, "8-128"),
        ({"password": "onlyletters"}, "letter and one digit"),
        ({"password": "1234567890"}, "letter and one digit"),
        ({"password": "é" * 40 + "1"}, "72 bytes"),
        ({"email": "not-an-email"}, "email"),
    ],
)
def test_registration_validation(client, overrides, fragment):

    response = register(client, **overrides)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert fragment.lower() in body["detail"].lower()


def test_registration_strips_name_and_lowercases_email(client):

    email = f"MiXeD-{uuid.uuid4().hex[:6]}@Example.COM"

    response = register(client, name="  Bob  ", email=f"  {email}  ")

    assert response.status_code == 200
    assert response.json()["name"] == "Bob"
    assert response.json()["email"] == email.lower()

    duplicate = register(client, email=email.upper())
    assert duplicate.status_code == 400
    assert duplicate.json() == {"detail": "Email already registered.", "code": "bad_request"}


def test_login_is_case_insensitive_and_rejects_bad_password(client, make_user):

    user = make_user()

    ok = client.post("/auth/login", json={"email": user["email"].upper(), "password": user["password"]})
    assert ok.status_code == 200

    bad = client.post("/auth/login", json={"email": user["email"], "password": "Wrong12345"})
    assert bad.status_code == 401
    assert bad.json() == {"detail": "Invalid email or password.", "code": "unauthorized"}


def test_login_with_overlong_password_is_422_not_a_crash(client, user):

    response = client.post("/auth/login", json={"email": user["email"], "password": "a1" * 100})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def test_token_claims(user):

    claims = jwt.decode(user["token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert claims["user_id"] == user["id"]
    assert claims["tv"] == 0
    assert len(claims["jti"]) == 32
    assert "iat" in claims and "exp" in claims
    assert "email" not in claims


def test_logout_revokes_all_existing_tokens(client, make_user):

    user = make_user()

    second = client.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    other_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

    assert client.get("/auth/profile", headers=user["headers"]).status_code == 200

    assert client.post("/auth/logout", headers=user["headers"]).status_code == 200

    for headers in (user["headers"], other_headers):
        response = client.get("/auth/profile", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has been revoked."

    fresh = client.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    fresh_headers = {"Authorization": f"Bearer {fresh.json()['access_token']}"}
    assert client.get("/auth/profile", headers=fresh_headers).status_code == 200


def forge(claims):

    return {"Authorization": "Bearer " + jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}


def test_token_version_mismatch_is_rejected(client, user):

    now = datetime.now(UTC)

    headers = forge({"user_id": user["id"], "tv": 7, "jti": "x", "iat": now, "exp": now + timedelta(minutes=5)})

    response = client.get("/auth/profile", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked."


def test_user_is_looked_up_by_user_id_claim(client, user):

    now = datetime.now(UTC)
    exp = now + timedelta(minutes=5)

    # A token naming the user by email only is not accepted.
    by_email = forge({"email": user["email"], "tv": 0, "iat": now, "exp": exp})
    assert client.get("/auth/profile", headers=by_email).status_code == 401

    unknown = forge({"user_id": str(uuid.uuid4()), "tv": 0, "iat": now, "exp": exp})
    assert client.get("/auth/profile", headers=unknown).status_code == 401

    good = forge({"user_id": user["id"], "tv": 0, "iat": now, "exp": exp})
    assert client.get("/auth/profile", headers=good).json()["email"] == user["email"]


def test_expired_and_wrongly_signed_tokens_are_rejected(client, user):

    now = datetime.now(UTC)

    expired = forge({"user_id": user["id"], "tv": 0, "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)})
    assert client.get("/auth/profile", headers=expired).status_code == 401

    wrong_key = jwt.encode(
        {"user_id": user["id"], "tv": 0, "exp": now + timedelta(minutes=5)}, "another-key-" * 4, algorithm="HS256"
    )
    assert client.get("/auth/profile", headers={"Authorization": f"Bearer {wrong_key}"}).status_code == 401


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_login_is_rate_limited(client, user):

    statuses = [
        client.post("/auth/login", json={"email": user["email"], "password": "Wrong12345"}).status_code
        for _ in range(6)
    ]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429

    limited = client.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    assert limited.status_code == 429
    assert limited.json() == {"detail": "Too many requests. Please try again later.", "code": "rate_limited"}
    assert limited.headers["Retry-After"] == "60"


def test_register_is_rate_limited(client):

    statuses = [register(client).status_code for _ in range(6)]

    assert statuses == [200] * 5 + [429]
