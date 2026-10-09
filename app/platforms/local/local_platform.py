import os
from pathlib import Path

from app.platforms.base_platform import BasePlatform
from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import EXCLUDED_REASON, is_excluded, is_supported, process_files, schedule_key
from app.database.db import SessionLocal
from app.database.local_storage_service import get_local_folders


class LocalPlatform(BasePlatform):

    def __init__(self, folders=None):

        if folders is None:
            folders = []

        self.folders = folders

    def index(self, ctx):

        from app.core.local_folders import is_allowed_folder
        from app.services.indexing_pipeline import index_local_file

        with SessionLocal() as db:
            stored = [folder.folder_path for folder in get_local_folders(db, ctx.user_id)]

        folders = []

        for raw in stored:
            try:
                resolved = Path(raw).resolve(strict=True)
            except OSError:
                ctx.record_error(raw, FileNotFoundError("Folder no longer exists."))
                continue
            # Same rules as registration (no roots, inside ALLOWED_LOCAL_ROOTS).
            if resolved.is_dir() and is_allowed_folder(resolved):
                folders.append(str(resolved))

        if not folders:
            raise PlatformPreconditionError("No valid local folders are registered.")

        self.folders = folders
        ctx.allowed_roots.extend(Path(folder) for folder in folders)

        supported, skipped = self.scan(folders)

        excluded = [path for path in supported if is_excluded(path)]
        supported = [path for path in supported if not is_excluded(path)]
        record_excluded(ctx.user_id, excluded)

        ctx.add_skipped(skipped + len(excluded))
        ctx.set_total(len(supported))

        supported.sort(key=local_schedule_key)

        process_files(
            ctx,
            supported,
            file_ref=lambda path: path,
            handle=lambda _position, path: index_local_file(
                ctx.user_id,
                path,
                temp_dir=ctx.temp_dir
            )
        )

        removed = sync_deleted_sources(ctx.user_id, folders)

        if removed:
            ctx.report_progress(force=True)

    @staticmethod
    def scan(folders):
        """(supported file paths, number of skipped entries).

        Skipped = unsupported files (not part of the progress denominator).
        Sub-folders are walked, not skipped, so they are not counted."""

        supported = []
        skipped = 0

        for folder in folders:

            if not os.path.isdir(folder):
                continue

            for root, _dirnames, filenames in os.walk(folder):

                for name in filenames:
                    if is_supported(name):
                        supported.append(os.path.join(root, name))
                    else:
                        skipped += 1

        return supported, skipped

    def list_files(self):

        return self.scan(self.folders)[0]


def local_schedule_key(path: str):
    """Documents -> images -> audio -> video, small first (see schedule_key)."""

    from app.config.file_types import file_type_for

    try:
        size = os.path.getsize(path)
    except OSError:
        size = None
    return schedule_key(file_type_for(path), size, path)


def record_excluded(user_id, paths) -> None:
    """Ledger rows for excluded files, so they are not reconsidered while unchanged."""

    from app.services import index_store
    from app.services.indexing_pipeline import local_meta

    for path in paths:
        meta = local_meta(user_id, path)
        if index_store.needs_index(meta.user_id, "local", meta.source_id, meta.version):
            index_store.record_status(meta, "excluded", error=EXCLUDED_REASON)


def sync_deleted_sources(user_id, folders) -> int:
    """Drop this user's local sources that no longer exist, or that are no
    longer under one of the user's CURRENT folders (or their upload dir).
    Strictly per user: other users' rows and vectors are never touched."""

    from app.core.ownership import user_upload_dir
    from app.core.paths import is_within
    from app.services import index_store

    bases = [Path(os.path.realpath(folder)) for folder in folders]
    bases.append(Path(os.path.realpath(user_upload_dir(user_id))))

    stale = []

    for row in index_store.list_sources(user_id, "local"):

        path = Path(row.display_path)

        if not path.is_file() or not any(is_within(path, base) for base in bases):
            stale.append(row.source_id)

    return index_store.delete_sources(user_id, "local", stale)
