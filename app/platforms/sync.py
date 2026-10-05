"""The sync loop shared by the cloud connectors (Google Drive, GitHub).

1. The connector lists REMOTE METADATA only (id, name, version, size).
2. Unsupported types and files over MAX_DOWNLOAD_MB are recorded in the
   ledger with their version and counted as skipped - never downloaded.
3. index_store.needs_index(user, platform, source_id, version) decides what
   to fetch: unchanged files are skipped without downloading (BUG-05).
4. Only new/changed files are downloaded, to a sanitized unique name inside
   the job's temp dir, indexed, and deleted again.
5. Deletion sync: if (and only if) the listing was complete, every ledger
   source of this user/platform that was not listed is removed (BUG-12).
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from app.core.config import settings
from app.platforms.indexing import process_files
from app.services import index_store
from app.services.index_store import FileMeta


logger = logging.getLogger("cogniseek.sync")


@dataclass
class RemoteFile:

    meta: FileMeta
    # Extension of the file as it will be stored locally (".pdf", ".docx", ...).
    extension: str
    size: Optional[int]
    # download(target_path) -> local path, or None when the content turns out
    # not to be indexable (e.g. a Git LFS pointer).
    download: Callable[[Path], Optional[str]]


@dataclass
class SyncResult:

    listed: int = 0
    unchanged: int = 0
    skipped: int = 0
    to_index: int = 0
    deleted: int = 0
    deletion_skipped: bool = False


def temp_name(source_id: str, extension: str) -> str:
    """Never the raw remote name: '/' and Windows-illegal characters can't
    break the path, and two files with the same name can't collide."""

    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]
    extension = extension if extension and extension.startswith(".") and len(extension) <= 12 else ""

    return f"{digest}{extension.lower()}"


def sync_remote(ctx, platform: str, files: List[RemoteFile], listing_complete: bool) -> SyncResult:

    from app.services.indexing_pipeline import index_source

    result = SyncResult(listed=len(files))
    seen = set()
    work: List[RemoteFile] = []

    for remote in files:

        meta = remote.meta
        seen.add(meta.source_id)

        if not index_store.needs_index(meta.user_id, platform, meta.source_id, meta.version):
            result.unchanged += 1
            continue

        if meta.file_type == "unsupported":
            index_store.record_status(meta, "unsupported")
            result.skipped += 1
            continue

        if remote.size is not None and remote.size > settings.max_download_bytes:
            index_store.record_status(meta, "too_large", error=f"Larger than {settings.MAX_DOWNLOAD_MB} MB")
            result.skipped += 1
            continue

        work.append(remote)

    result.to_index = len(work)

    ctx.add_skipped(result.unchanged + result.skipped)
    ctx.set_total(len(work))

    def handle(position: int, remote: RemoteFile):

        target = ctx.file_dir(position) / temp_name(remote.meta.source_id, remote.extension)
        local_path = None

        try:
            local_path = remote.download(target)
            ctx.file_downloaded()

            if local_path is None:
                index_store.record_status(remote.meta, "unsupported")
                return

            index_source(remote.meta, local_path, temp_dir=ctx.temp_dir, force=True)

        finally:
            for path in {str(target), local_path}:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass   # the job temp dir is removed by the worker anyway

    process_files(ctx, work, file_ref=lambda remote: remote.meta.display_path, handle=handle)

    # ---- deletion sync --------------------------------------------------

    if not listing_complete:
        result.deletion_skipped = True
        logger.warning(
            "%s listing for user %s was incomplete: deletion sync skipped", platform, ctx.user_id
        )
        return result

    if ctx.is_cancelled():
        result.deletion_skipped = True
        return result

    stale = [
        row.source_id
        for row in index_store.list_sources(ctx.user_id, platform)
        if row.source_id not in seen
    ]

    result.deleted = index_store.delete_sources(ctx.user_id, platform, stale)

    if result.deleted:
        logger.info("%s: removed %d deleted source(s) for user %s", platform, result.deleted, ctx.user_id)

    return result
