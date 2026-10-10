"""One entry point to index a file: ledger check -> extract -> store.

Replaces process_uploaded_file / index_file and the old file-based indexes.
"""

import mimetypes
import os
from datetime import UTC, datetime

from app.config.file_types import file_type_for
from app.core.timing import file_scope, span
from app.scheduler.errors import sanitize_error
from app.services import index_store
from app.services.index_store import FileMeta
from app.services.indexers.audio_indexer import build_audio_points
from app.services.indexers.document_indexer import build_document_points
from app.services.indexers.image_indexer import build_image_points
from app.services.indexers.video_indexer import build_video_points

BUILDERS = {
    "document": build_document_points,
    "image": build_image_points,
    "audio": build_audio_points,
    "video": build_video_points,
}


# ----------------------------------------------------------------------
# Source identity (A1)
# ----------------------------------------------------------------------

def local_source_id(path: str) -> str:
    """Absolute, symlink-free, case-normalized (Windows) path."""

    return os.path.normcase(os.path.realpath(path))


def github_source_id(owner: str, repo: str, path: str) -> str:

    return f"{owner}/{repo}:{path}"


def guess_mime(name: str) -> str | None:

    return mimetypes.guess_type(name or "")[0]


def parse_rfc3339(value: str | None) -> datetime | None:
    """'2026-10-06T15:25:53.000Z' -> aware UTC datetime (None if absent/invalid)."""

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def local_meta(user_id, path: str) -> FileMeta:

    real = os.path.realpath(path)
    stat = os.stat(real)

    return FileMeta(
        user_id=str(user_id),
        platform="local",
        source_id=local_source_id(path),
        file_name=os.path.basename(real),
        display_path=real,
        file_type=file_type_for(real) or "unsupported",
        version=repr(stat.st_mtime),
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        mime_type=guess_mime(real)
    )


def drive_meta(user_id, file: dict, extension: str) -> FileMeta:
    """`extension` is the type the file will have locally (exports: .docx/.pptx/.csv)."""

    version = file.get("modifiedTime")

    if file.get("md5Checksum"):
        version = f"{version}|{file['md5Checksum']}"

    return FileMeta(
        user_id=str(user_id),
        platform="google_drive",
        source_id=file["id"],
        file_name=file["name"],
        display_path=file["name"],
        file_type=file_type_for(f"x{extension}") or "unsupported",
        version=version,
        web_view_link=file.get("webViewLink"),
        size_bytes=int(file["size"]) if str(file.get("size") or "").isdigit() else None,
        modified_at=parse_rfc3339(file.get("modifiedTime")),
        mime_type=file.get("mimeType") or guess_mime(f"x{extension}")
    )


def github_meta(user_id, owner: str, repo: str, file: dict, default_branch: str | None = None) -> FileMeta:

    path = file["path"]

    return FileMeta(
        user_id=str(user_id),
        platform="github",
        source_id=github_source_id(owner, repo, path),
        file_name=os.path.basename(path),
        display_path=f"{owner}/{repo}/{path}",
        file_type=file_type_for(path) or "unsupported",
        version=file.get("sha"),
        owner=owner,
        repo=repo,
        default_branch=default_branch,
        size_bytes=file.get("size"),
        mime_type=guess_mime(path)
    )


# ----------------------------------------------------------------------
# Indexing
# ----------------------------------------------------------------------

def index_source(meta: FileMeta, local_path: str, temp_dir=None, force: bool = False) -> str:
    """Index one file. Returns 'skipped' | 'indexed' | 'no_content' | 'unsupported'.

    Raises on extraction errors (after recording status 'failed' in the
    ledger), so the job counts the file as failed.
    """

    with file_scope(meta.file_type):

        if not force:
            with span("ledger"):
                changed = index_store.needs_index(meta.user_id, meta.platform, meta.source_id, meta.version)
            if not changed:
                return "skipped"

        builder = BUILDERS.get(meta.file_type)

        if builder is None:
            index_store.record_status(meta, "unsupported")
            return "unsupported"

        try:
            points = builder(local_path, temp_dir)
        except Exception as error:
            index_store.record_status(meta, "failed", error=sanitize_error(error))
            raise

        row = index_store.upsert_file(meta, points)

        return row.status


def index_local_file(user_id, path: str, temp_dir=None, force: bool = False) -> str:

    return index_source(local_meta(user_id, path), path, temp_dir=temp_dir, force=force)
