from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

import uuid

from .db import Base


# ==========================================================
# USERS
# ==========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    full_name = Column(String)

    password_hash = Column(Text)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    last_login = Column(
        DateTime,
        server_default=func.now(),
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
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    platform = Column(String)

    status = Column(
        String,
        default="not_started"
    )

    total_files = Column(
        Integer,
        default=0
    )

    indexed_files = Column(
        Integer,
        default=0
    )

    current_file = Column(
        Text,
        default=""
    )

    started_at = Column(DateTime)

    completed_at = Column(DateTime)

    last_index_time = Column(DateTime)

    needs_reindex = Column(
        Boolean,
        default=False
    )


# ==========================================================
# LOCAL STORAGE FOLDERS
# ==========================================================

class LocalStorageFolder(Base):

    __tablename__ = "local_storage_folders"

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

    folder_path = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# ==========================================================
# INDEXED FILES
# ==========================================================

class IndexedFile(Base):

    __tablename__ = "indexed_files"

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

    external_file_id = Column(Text)

    file_path = Column(Text)

    file_name = Column(Text)

    file_hash = Column(Text)

    modified_time = Column(DateTime)

    indexed_at = Column(
        DateTime,
        server_default=func.now()
    )


# ==========================================================
# SEARCH CACHE
# ==========================================================

class SearchCache(Base):

    __tablename__ = "search_cache"

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

    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("indexed_files.id")
    )

    embedding_path = Column(Text)

    cache_updated_at = Column(
        DateTime,
        server_default=func.now()
    )


# ==========================================================
# INDEXING HISTORY
# ==========================================================

class IndexingHistory(Base):

    __tablename__ = "indexing_history"

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

    started_at = Column(DateTime)

    completed_at = Column(DateTime)

    files_indexed = Column(
        Integer,
        default=0
    )

    status = Column(String)

    remarks = Column(Text)