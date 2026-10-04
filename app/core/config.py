"""Centralized application settings, loaded from environment / .env."""

import secrets
import warnings
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True
    )

    ENV: Literal["development", "production"] = "development"

    # Database / vector store
    DATABASE_URL: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Auth
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # HTTP
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:5173"
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # OAuth client config files
    GITHUB_OAUTH_CONFIG_PATH: str = "credentials/github_oauth.json"
    GOOGLE_CLIENT_SECRET_PATH: str = "credentials/client_secret.json"

    # Filesystem
    DATA_DIR: str = "data"
    TEMP_DIR: str = "temp"

    @property
    def cors_origins_list(self) -> List[str]:

        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def check_jwt_secret(self):

        key = self.JWT_SECRET_KEY

        if key and len(key) >= MIN_JWT_SECRET_LENGTH:
            return self

        if self.ENV == "production":
            raise ValueError(
                "JWT_SECRET_KEY must be set and at least "
                f"{MIN_JWT_SECRET_LENGTH} characters in production."
            )

        if not key:
            self.JWT_SECRET_KEY = secrets.token_urlsafe(48)
            warnings.warn(
                "JWT_SECRET_KEY is not set: using a random development key. "
                "Tokens will be invalidated on every restart.",
                stacklevel=2
            )
        else:
            warnings.warn(
                f"JWT_SECRET_KEY is shorter than {MIN_JWT_SECRET_LENGTH} "
                "characters. This is only allowed in development.",
                stacklevel=2
            )

        return self


@lru_cache
def get_settings() -> Settings:

    return Settings()


settings = get_settings()
