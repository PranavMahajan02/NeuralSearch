import pytest

from app.core.config import Settings


@pytest.mark.slow
def test_app_imports(app):

    assert app.title == "CogniSeek API"


@pytest.mark.slow
def test_root_returns_200(client):

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "CogniSeek Backend Running"}


def test_settings_load_from_env(monkeypatch):

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    monkeypatch.setenv("QDRANT_HOST", "qdrant-test")
    monkeypatch.setenv("QDRANT_PORT", "7333")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 40)
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == "postgresql://u:p@db:5432/x"
    assert settings.QDRANT_HOST == "qdrant-test"
    assert settings.QDRANT_PORT == 7333
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert settings.cors_origins_list == ["http://a.test", "http://b.test"]


def test_production_rejects_weak_jwt_secret(monkeypatch):

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    monkeypatch.setenv("JWT_SECRET_KEY", "too-short")

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_development_generates_jwt_secret_when_missing(monkeypatch):

    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.warns(UserWarning, match="JWT_SECRET_KEY"):
        settings = Settings(_env_file=None)

    assert len(settings.JWT_SECRET_KEY) >= 32
