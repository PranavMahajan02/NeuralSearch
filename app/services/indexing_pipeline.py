"""One entry point to index a file: ledger check -> extract -> store.

Replaces process_uploaded_file / index_file and the old file-based indexes.
"""

import os
from typing import Optional

from app.config.file_types import file_type_for
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


def local_meta(user_id, path: str) -> FileMeta:

    real = os.path.realpath(path)

    return FileMeta(
        user_id=str(user_id),
        platform="local",
        source_id=local_source_id(path),
        file_name=os.path.basename(real),
        display_path=real,
        file_type=file_type_for(real) or "unsupported",
        version=repr(os.path.getmtime(real))
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
        web_view_link=file.get("webViewLink")
    )


def github_meta(user_id, owner: str, repo: str, file: dict, default_branch: Optional[str] = None) -> FileMeta:

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
        default_branch=default_branch
    )


# ----------------------------------------------------------------------
# Indexing
# ----------------------------------------------------------------------

def index_source(meta: FileMeta, local_path: str, temp_dir=None, force: bool = False) -> str:
    """Index one file. Returns 'skipped' | 'indexed' | 'no_content' | 'unsupported'.

    Raises on extraction errors (after recording status 'failed' in the
    ledger), so the job counts the file as failed.
    """

    if not force and not index_store.needs_index(meta.user_id, meta.platform, meta.source_id, meta.version):
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
