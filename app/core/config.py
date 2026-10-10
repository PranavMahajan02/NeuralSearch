"""Centralized application settings, loaded from environment / .env."""

import secrets
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


def _split_csv(value: str) -> list[str]:

    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    ENV: Literal["development", "production"] = "development"

    # Database / vector store
    DATABASE_URL: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    # ":memory:" runs an in-process Qdrant (tests). Empty = QDRANT_HOST/PORT.
    QDRANT_LOCATION: str = ""
    # Collections are <prefix>_text, _image, _audio, _video, _video_frames.
    QDRANT_COLLECTION_PREFIX: str = "cogniseek_v2"
    # Qdrant API key (QDRANT__SERVICE__API_KEY on the server). Required in production.
    QDRANT_API_KEY: str | None = None

    # Redis for shared rate-limit counters. Required in production; empty in
    # development = in-memory counters (per process, reset on restart).
    REDIS_URL: str = ""

    # Uvicorn worker processes. Keep 1: the indexing worker runs inside the API
    # process and the models (GPU) are loaded once per process.
    WORKERS: int = 1

    # Logs: "text" (development) or "json" (production default when empty).
    LOG_FORMAT: Literal["", "text", "json"] = ""
    LOG_LEVEL: str = "INFO"

    # GET /metrics (Prometheus). Never proxied publicly (see deploy/Caddyfile).
    METRICS_ENABLED: bool = True

    # Auth
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Fernet key for OAuth tokens stored in the DB.
    TOKEN_ENCRYPTION_KEY: str | None = None

    # Rate limit for /auth/login and /auth/register (slowapi syntax).
    AUTH_RATE_LIMIT: str = "5/minute"
    # Per user (per IP when anonymous).
    SEARCH_RATE_LIMIT: str = "60/minute"
    OAUTH_RATE_LIMIT: str = "10/minute"

    # HTTP
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8000"
    FRONTEND_URL: str = "http://127.0.0.1:3000"

    # OAuth client config files
    GITHUB_OAUTH_CONFIG_PATH: str = "credentials/github_oauth.json"
    GOOGLE_CLIENT_SECRET_PATH: str = "credentials/client_secret.json"
    # Must be registered in the Google Cloud console (Web application client).
    # Empty = BACKEND_PUBLIC_URL + /platforms/google-drive/callback
    GOOGLE_REDIRECT_URI: str = ""

    # Connectors
    MAX_DOWNLOAD_MB: int = 200
    # Per-file indexing limits: text beyond them is truncated (ledger note).
    # Generated/noise files never indexed (base-name globs, case-insensitive).
    INDEX_EXCLUDE_GLOBS: str = (
        "*.log,*.lock,*.min.js,*.map,*_log.txt,project_files.txt,package-lock.json,yarn.lock,poetry.lock"
    )
    MAX_TEXT_CHARS_PER_FILE: int = 2_000_000
    MAX_CHUNKS_PER_FILE: int = 2000
    # Points per Qdrant upsert request (one huge request exceeds Qdrant's
    # 32 MB request limit and the connection is dropped).
    QDRANT_UPSERT_BATCH: int = 256
    GITHUB_INCLUDE_FORKS: bool = False
    GITHUB_INCLUDE_ARCHIVED: bool = False

    # OCR fallback for scanned / image-heavy PDF pages.
    OCR_MAX_PAGES: int = 20
    # PaddleOCR device: "auto" (GPU when a CUDA build of Paddle is installed,
    # see requirements-gpu.txt), "cpu" or "gpu".
    OCR_DEVICE: Literal["auto", "cpu", "gpu"] = "auto"
    # faster-whisper batched pipeline (0 = off, the sequential decoder).
    WHISPER_BATCH_SIZE: int = 0
    # Files processed at once per job (downloads + CPU extraction overlap with
    # GPU work; the GPU sections stay serialized). 1 = strictly sequential.
    INDEX_IO_WORKERS: int = 4
    # Upper bound on files in flight (bounded memory / temp disk), >= workers.
    INDEX_PREFETCH: int = 8
    # One lock for ALL GPU model calls instead of one per model. Off: measured
    # 115 s vs 93 s (per-model locks) on the benchmark set - different models
    # overlapping on the GPU is faster (docs/perf/RESULTS.md).
    GPU_SERIALIZE: bool = False

    # Models: load all of them at startup (True) or on first use (False).
    PRELOAD_MODELS: bool = True
    # Poppler binaries for OCR of scanned PDFs (empty = on PATH).
    POPPLER_PATH: str = ""

    # Filesystem
    DATA_DIR: str = "data"
    TEMP_DIR: str = "temp"
    MAX_UPLOAD_MB: int = 100

    # Comma list of directories under which local folders may be registered.
    # Empty = the home directory of the user running the backend.
    ALLOWED_LOCAL_ROOTS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:

        return _split_csv(self.CORS_ORIGINS)

    @property
    def allowed_local_roots_list(self) -> list[str]:

        return _split_csv(self.ALLOWED_LOCAL_ROOTS) or [str(Path.home())]

    @property
    def google_redirect_uri(self) -> str:

        return self.GOOGLE_REDIRECT_URI or f"{self.BACKEND_PUBLIC_URL}/platforms/google-drive/callback"

    @property
    def max_download_bytes(self) -> int:

        return self.MAX_DOWNLOAD_MB * 1024 * 1024

    @property
    def max_upload_bytes(self) -> int:

        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:

        return self.ENV == "production"

    @property
    def log_format(self) -> str:

        return self.LOG_FORMAT or ("json" if self.is_production else "text")

    @model_validator(mode="after")
    def check_token_encryption_key(self):

        key = self.TOKEN_ENCRYPTION_KEY

        if key:
            try:
                Fernet(key.encode())
            except (ValueError, TypeError):
                raise ValueError("TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from None
            return self

        if self.is_production:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be set in production.")

        self.TOKEN_ENCRYPTION_KEY = Fernet.generate_key().decode()
        warnings.warn(
            "TOKEN_ENCRYPTION_KEY is not set: using a random development key. "
            "Stored OAuth tokens will be unreadable after a restart.",
            stacklevel=2,
        )

        return self

    @model_validator(mode="after")
    def check_jwt_secret(self):

        key = self.JWT_SECRET_KEY

        if key and len(key) >= MIN_JWT_SECRET_LENGTH:
            return self

        if self.ENV == "production":
            raise ValueError(
                f"JWT_SECRET_KEY must be set and at least {MIN_JWT_SECRET_LENGTH} characters in production."
            )

        if not key:
            self.JWT_SECRET_KEY = secrets.token_urlsafe(48)
            warnings.warn(
                "JWT_SECRET_KEY is not set: using a random development key. "
                "Tokens will be invalidated on every restart.",
                stacklevel=2,
            )
        else:
            warnings.warn(
                f"JWT_SECRET_KEY is shorter than {MIN_JWT_SECRET_LENGTH} "
                "characters. This is only allowed in development.",
                stacklevel=2,
            )

        return self

    @model_validator(mode="after")
    def check_production_services(self):
        """Production needs an authenticated Qdrant and shared rate-limit storage
        (checked last, after the secrets)."""

        if not self.is_production:
            return self

        if not self.QDRANT_LOCATION and not self.QDRANT_API_KEY:
            raise ValueError("QDRANT_API_KEY must be set in production.")

        if not self.REDIS_URL:
            raise ValueError("REDIS_URL must be set in production (rate limits are shared and persistent).")

        return self


@lru_cache
def get_settings() -> Settings:

    return Settings()


settings = get_settings()
