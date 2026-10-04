from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

import uuid

from .db import Base


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

    access_token = Column(Text)

    refresh_token = Column(Text)

    token_json = Column(Text)

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

class IndexingJob(Base):

    __tablename__ = "indexing_jobs"

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
        default="not_started",
        server_default=text("'not_started'::character varying")
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


# ==========================================================
# LOCAL STORAGE FOLDERS
# ==========================================================

class LocalStorageFolder(Base):

    __tablename__ = "local_storage_folders"

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
# INDEXED FILES
# ==========================================================

class IndexedFile(Base):

    __tablename__ = "indexed_files"

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

    external_file_id = Column(Text)

    file_path = Column(Text)

    file_name = Column(Text)

    file_hash = Column(Text)

    modified_time = Column(DateTime)

    indexed_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP")
    )


# ==========================================================
# SEARCH CACHE
# ==========================================================

class SearchCache(Base):

    __tablename__ = "search_cache"

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

    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("indexed_files.id", ondelete="CASCADE")
    )

    embedding_path = Column(Text)

    cache_updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP")
    )


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
