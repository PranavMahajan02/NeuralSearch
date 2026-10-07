"""The ONLY module that writes or deletes vectors and ledger rows.

Qdrant holds the vectors (one point per chunk), Postgres `indexed_files`
holds one row per source file. Both are always keyed by
(user_id, platform, source_id), so every write and delete is per user.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    Range,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.db import SessionLocal
from app.database.models import IndexedFile, LEDGER_SKIP_STATUSES
from app.vectorstore.client import get_client
from app.vectorstore.config import all_collections, collection_for_type
from app.vectorstore.query import user_filter
from app.vectorstore.schema import point_id


logger = logging.getLogger("cogniseek.index_store")


@dataclass
class FileMeta:
    """Identity and display data of one source file."""

    user_id: str
    platform: str
    source_id: str
    file_name: str
    display_path: str
    file_type: str          # document | image | audio | video
    version: Optional[str]
    owner: Optional[str] = None
    repo: Optional[str] = None
    default_branch: Optional[str] = None     # GitHub
    web_view_link: Optional[str] = None      # Google Drive
    size_bytes: Optional[int] = None
    modified_at: Optional[datetime] = None   # naive UTC
    mime_type: Optional[str] = None


@dataclass
class IndexPoint:
    """One vector to store. `type` is document|image|audio|video|video_frame."""

    type: str
    vector: List[float]
    chunk_index: int
    chunk: str
    frame_number: Optional[int] = None
    extra: Dict = field(default_factory=dict)


def _payload(meta: FileMeta, point: IndexPoint) -> dict:

    payload = {
        "user_id": str(meta.user_id),
        "platform": meta.platform,
        "source_id": meta.source_id,
        "file": meta.file_name,
        "path": meta.display_path,
        "type": point.type,
        # local: mtime as float; drive: modifiedTime; github: blob sha.
        "version": float(meta.version) if meta.platform == "local" and meta.version else meta.version,
        "chunk_index": point.chunk_index,
        "chunk": point.chunk or "",
    }

    if point.frame_number is not None:
        payload["frame_number"] = point.frame_number

    if meta.platform == "github":
        payload["owner"] = meta.owner
        payload["repo"] = meta.repo

    return payload


def _point_struct(meta: FileMeta, point: IndexPoint) -> PointStruct:

    return PointStruct(
        id=point_id(
            str(meta.user_id), meta.platform, meta.source_id,
            point.type, point.chunk_index, point.frame_number
        ),
        vector=list(point.vector),
        payload=_payload(meta, point)
    )


class Points(list):
    """A builder's points plus an optional ledger note (e.g. 'truncated: ...')."""

    def __init__(self, items=(), note: Optional[str] = None):

        super().__init__(items)
        self.note = note


class VectorStoreWriteError(Exception):
    """Qdrant rejected or dropped a write. The message is shown to the user;
    the raw exception is only logged."""

    user_facing = True


_TOO_LARGE_HINTS = ("10053", "10054", "aborted", "reset", "413", "too large", "payload")


def _write_failed(action: str, error: Exception) -> VectorStoreWriteError:

    logger.error("Qdrant %s failed: %r", action, error, exc_info=(type(error), error, error.__traceback__))

    text = f"{type(error).__name__} {error}".lower()
    reason = "request too large" if any(h in text for h in _TOO_LARGE_HINTS) else "vector store unavailable"

    return VectorStoreWriteError(f"Could not save vectors ({reason})")


def _batches(items: List, size: int):

    size = max(1, int(size))

    for start in range(0, len(items), size):
        yield items[start:start + size]


def _source_filter(user_id, platform: str, source_id: str, **extra) -> Filter:

    return user_filter(str(user_id), platform, source_id=source_id, **extra)


# ----------------------------------------------------------------------
# Writes
# ----------------------------------------------------------------------

def upsert_file(meta: FileMeta, points: List[IndexPoint], session_factory=SessionLocal) -> IndexedFile:
    """Store the points of one file, then drop its stale chunks, then record it.

    Order matters: new points are written first (deterministic ids overwrite
    the old chunk 0..n-1 in place), and only then are leftover chunks with
    chunk_index >= n deleted. A concurrent search sees old or new chunks,
    never an empty file.

    Points are sent in batches of QDRANT_UPSERT_BATCH. If any batch fails
    nothing is pruned, the ledger keeps the previous version and records
    'failed' (the file is retried next run), and VectorStoreWriteError is raised.
    """

    client = get_client()

    by_type: Dict[str, List[IndexPoint]] = {}
    for point in points:
        by_type.setdefault(point.type, []).append(point)

    try:
        for point_type, group in by_type.items():
            for batch in _batches(group, settings.QDRANT_UPSERT_BATCH):
                client.upsert(
                    collection_name=collection_for_type(point_type),
                    points=[_point_struct(meta, p) for p in batch],
                    wait=True
                )
    except Exception as error:
        failure = _write_failed("upsert", error)
        _record_failure(meta, str(failure), session_factory)
        raise failure from None

    # Prune: per type, everything at or beyond the new chunk count.
    for point_type in _types_for(meta.file_type):

        group = by_type.get(point_type, [])
        keep = (max(p.chunk_index for p in group) + 1) if group else 0

        client.delete(
            collection_name=collection_for_type(point_type),
            points_selector=FilterSelector(
                filter=Filter(
                    must=_source_filter(meta.user_id, meta.platform, meta.source_id).must + [
                        FieldCondition(key="chunk_index", range=Range(gte=keep))
                    ]
                )
            ),
            wait=True
        )

    status = "indexed" if points else "no_content"

    return _record(meta, status=status, chunk_count=len(points),
                   error=getattr(points, "note", None), session_factory=session_factory)


def _record_failure(meta: FileMeta, message: str, session_factory) -> None:
    """status 'failed' with the PREVIOUS version kept, so the file is retried."""

    with session_factory() as db:
        row = _get_row(db, meta.user_id, meta.platform, meta.source_id)
        previous = row.version if row is not None else None

    _record(FileMeta(**{**meta.__dict__, "version": previous}), status="failed", chunk_count=None,
            error=message, session_factory=session_factory)


def record_status(meta: FileMeta, status: str, error: Optional[str] = None, session_factory=SessionLocal) -> IndexedFile:
    """Ledger-only update (failed / unsupported). Existing vectors are kept
    for 'failed' so a transient error does not drop a file from search."""

    return _record(meta, status=status, chunk_count=None, error=error, session_factory=session_factory)


def _record(meta: FileMeta, status: str, chunk_count, error=None, session_factory=SessionLocal) -> IndexedFile:

    now = datetime.utcnow()

    with session_factory() as db:

        row = _get_row(db, meta.user_id, meta.platform, meta.source_id)

        if row is None:
            row = IndexedFile(
                user_id=meta.user_id,
                platform=meta.platform,
                source_id=meta.source_id,
                indexed_at=now
            )
            db.add(row)

        row.file_name = meta.file_name
        row.display_path = meta.display_path
        row.file_type = meta.file_type
        row.version = None if meta.version is None else str(meta.version)
        row.status = status
        row.error = error
        row.owner = meta.owner
        row.repo = meta.repo
        row.default_branch = meta.default_branch
        row.web_view_link = meta.web_view_link
        if meta.size_bytes is not None:
            row.size_bytes = meta.size_bytes
        if meta.modified_at is not None:
            row.modified_at = meta.modified_at
        if meta.mime_type is not None:
            row.mime_type = meta.mime_type
        row.updated_at = now

        if chunk_count is not None:
            row.chunk_count = chunk_count
            row.indexed_at = now

        db.commit()
        db.refresh(row)
        db.expunge(row)

        return row


def delete_file(user_id, platform: str, source_id: str, session_factory=SessionLocal) -> None:
    """Remove a source's points from every collection and its ledger row."""

    client = get_client()
    selector = FilterSelector(filter=_source_filter(user_id, platform, source_id))

    for name in all_collections():
        client.delete(collection_name=name, points_selector=selector, wait=True)

    with session_factory() as db:
        db.query(IndexedFile).filter(
            IndexedFile.user_id == user_id,
            IndexedFile.platform == platform,
            IndexedFile.source_id == source_id
        ).delete(synchronize_session=False)
        db.commit()


def delete_sources(user_id, platform: str, source_ids: Iterable[str], session_factory=SessionLocal) -> int:

    count = 0

    for source_id in source_ids:
        delete_file(user_id, platform, source_id, session_factory=session_factory)
        count += 1

    return count


def purge_platform(user_id, platform: str, session_factory=SessionLocal) -> int:
    """Delete every source of this user on this platform (disconnect + purge)."""

    client = get_client()
    selector = FilterSelector(filter=user_filter(str(user_id), platform))

    for name in all_collections():
        client.delete(collection_name=name, points_selector=selector, wait=True)

    with session_factory() as db:
        count = db.query(IndexedFile).filter(
            IndexedFile.user_id == user_id,
            IndexedFile.platform == platform
        ).delete(synchronize_session=False)
        db.commit()

    return count


# ----------------------------------------------------------------------
# Reads
# ----------------------------------------------------------------------

def _get_row(db: Session, user_id, platform: str, source_id: str) -> Optional[IndexedFile]:

    return db.query(IndexedFile).filter(
        IndexedFile.user_id == user_id,
        IndexedFile.platform == platform,
        IndexedFile.source_id == source_id
    ).first()


def get_source(user_id, platform: str, source_id: str, session_factory=SessionLocal) -> Optional[IndexedFile]:

    with session_factory() as db:
        row = _get_row(db, user_id, platform, source_id)
        if row is not None:
            db.expunge(row)
        return row


def list_sources(user_id, platform: str, session_factory=SessionLocal) -> List[IndexedFile]:

    with session_factory() as db:
        rows = db.query(IndexedFile).filter(
            IndexedFile.user_id == user_id,
            IndexedFile.platform == platform
        ).all()
        for row in rows:
            db.expunge(row)
        return rows


def needs_index(user_id, platform: str, source_id: str, version, session_factory=SessionLocal) -> bool:
    """False when this exact version was already handled (indexed, had no
    content, or is unsupported) - so empty/scanned files are not re-extracted
    on every run (BUG-16). Failed files are retried."""

    row = get_source(user_id, platform, source_id, session_factory=session_factory)

    if row is None:
        return True

    same_version = row.version is not None and version is not None and row.version == str(version)

    return not (same_version and row.status in LEDGER_SKIP_STATUSES)


def _types_for(file_type: str) -> List[str]:

    if file_type == "video":
        return ["video", "video_frame"]

    return [file_type]
