from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    Index,
    UniqueConstraint,
    text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

import uuid

from .db import Base
from app.core.crypto import EncryptedText


# Mirrors the live schema (see alembic/versions/0001_baseline.py).
# Python-side defaults are kept so ORM inserts behave as before.


# ==========================================================
# USERS
# ==========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False
    )

    full_name = Column(String(255))

    password_hash = Column(Text)

    # Bumped on logout; tokens carrying an older "tv" claim are rejected.
    token_version = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0")
    )

    created_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP")
    )

    last_login = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now()
    )


# ==========================================================
# PLATFORM CONNECTIONS
# ==========================================================

class PlatformConnection(Base):

    __tablename__ = "platform_connections"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    platform = Column(String)

    account_email = Column(String)

    account_name = Column(String)

    # Encrypted at rest (Fernet) - see app/core/crypto.py.
    access_token = Column(EncryptedText)

    refresh_token = Column(EncryptedText)

    token_json = Column(EncryptedText)

    token_type = Column(Text)

    connected = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# ==========================================================
# INDEXING JOBS
# ==========================================================

JOB_STATUSES = (
    "queued",
    "running",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled"
)

ACTIVE_JOB_STATUSES = ("queued", "running")

FINISHED_JOB_STATUSES = ("completed", "completed_with_errors", "failed", "cancelled")


class IndexingJob(Base):
    """One indexing run of one platform for one user (rows are never reused).

    State machine: see app/scheduler/jobs.py.
    """

    __tablename__ = "indexing_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in JOB_STATUSES) + ")",
            name="ck_indexing_jobs_status"
        ),
        Index("ix_indexing_jobs_status_created_at", "status", "created_at"),
        Index("ix_indexing_jobs_user_platform", "user_id", "platform"),
        # At most one queued/running job per user and platform (409 on enqueue).
        Index(
            "uq_indexing_jobs_one_active",
            "user_id",
            "platform",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')")
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    platform = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(30),
        nullable=False,
        default="queued",
        server_default=text("'queued'::character varying")
    )

    total_files = Column(
        Integer,
        default=0,
        server_default=text("0")
    )

    indexed_files = Column(
        Integer,
        default=0,
        server_default=text("0")
    )

    current_file = Column(
        Text,
        default="",
        server_default=text("''::text")
    )

    started_at = Column(DateTime)

    completed_at = Column(DateTime)

    last_index_time = Column(DateTime)

    needs_reindex = Column(
        Boolean,
        default=False,
        server_default=text("false")
    )

    # Progress: total_files counts supported files only; processed =
    # succeeded + failed. Unsupported files and folders go to skipped_files.
    processed_files = Column(Integer, nullable=False, default=0, server_default=text("0"))

    succeeded_files = Column(Integer, nullable=False, default=0, server_default=text("0"))

    failed_files = Column(Integer, nullable=False, default=0, server_default=text("0"))

    skipped_files = Column(Integer, nullable=False, default=0, server_default=text("0"))

    # Files actually fetched from the remote (0 on a run with no changes).
    downloaded_files = Column(Integer, nullable=False, default=0, server_default=text("0"))

    error_message = Column(Text)

    cancel_requested = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    heartbeat_at = Column(DateTime)


# ==========================================================
# INDEXING JOB ERRORS (per-file failures, capped per job)
# ==========================================================

class IndexingJobError(Base):

    __tablename__ = "indexing_job_errors"

    __table_args__ = (
        Index("ix_indexing_job_errors_job_id", "job_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("indexing_jobs.id", ondelete="CASCADE"),
        nullable=False
    )

    file_ref = Column(Text, nullable=False)

    error = Column(Text, nullable=False)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


# ==========================================================
# LOCAL STORAGE FOLDERS
# ==========================================================

class LocalStorageFolder(Base):

    __tablename__ = "local_storage_folders"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "folder_path",
            name="uq_local_storage_folders_user_path"
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    folder_path = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP")
    )


# ==========================================================
# INDEXED FILES (per-file ledger of the Qdrant index)
# ==========================================================

LEDGER_STATUSES = ("indexed", "no_content", "failed", "unsupported", "too_large", "excluded")

# A source in one of these states is not re-processed while its version is
# unchanged (failed files are retried on the next run).
LEDGER_SKIP_STATUSES = ("indexed", "no_content", "unsupported", "too_large", "excluded")


class IndexedFile(Base):
    """One row per indexed source (file) of a user on a platform.

    source_id: local = normcase(realpath), google_drive = file id,
    github = "owner/repo:path". version: mtime / modifiedTime / blob sha.
    """

    __tablename__ = "indexed_files"

    __table_args__ = (
        UniqueConstraint("user_id", "platform", "source_id", name="uq_indexed_files_source"),
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in LEDGER_STATUSES) + ")",
            name="ck_indexed_files_status"
        ),
        Index("ix_indexed_files_user_platform", "user_id", "platform"),
        # Trigram index: fuzzy file-name candidates for search (BUG-21).
        Index(
            "ix_indexed_files_file_name_trgm",
            "file_name",
            postgresql_using="gin",
            postgresql_ops={"file_name": "gin_trgm_ops"}
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    platform = Column(String(50), nullable=False)

    source_id = Column(Text, nullable=False)

    file_name = Column(Text, nullable=False)

    display_path = Column(Text, nullable=False)

    file_type = Column(String(20), nullable=False)

    version = Column(Text)

    status = Column(String(20), nullable=False)

    chunk_count = Column(Integer, nullable=False, default=0, server_default=text("0"))

    error = Column(Text)

    # GitHub only (needed to build the blob URL).
    owner = Column(Text)

    repo = Column(Text)

    default_branch = Column(Text)

    # Google Drive: the file's webViewLink (used by /open).
    web_view_link = Column(Text)

    indexed_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


# ==========================================================
# INDEXING HISTORY
# ==========================================================

class IndexingHistory(Base):

    __tablename__ = "indexing_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    platform = Column(String(50))

    started_at = Column(DateTime)

    completed_at = Column(DateTime)

    files_indexed = Column(
        Integer,
        default=0,
        server_default=text("0")
    )

    status = Column(String(30))

    remarks = Column(Text)


# ==========================================================
# OAUTH STATES (single-use CSRF state for OAuth redirects)
# ==========================================================

class OAuthState(Base):

    __tablename__ = "oauth_states"

    state = Column(
        String(128),
        primary_key=True
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    platform = Column(
        String(50),
        nullable=False
    )

    expires_at = Column(
        DateTime,
        nullable=False
    )

    used = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false")
    )

    # PKCE code_verifier (Google); kept server-side with the single-use state.
    code_verifier = Column(Text)

    created_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP")
    )
