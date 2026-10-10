"""Which files and platforms belong to a user.

Interim ownership model for Phase 1 (until user_id is stored on every vector in
Phase 3): a user owns a local path if it is inside one of their registered
local folders or their upload directory.
"""

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.local_folders import is_allowed_folder
from app.core.paths import UnsafePathError, is_within, resolve_in_any, resolve_safe
from app.database.local_storage_service import get_local_folders
from app.database.platform_connection_service import is_platform_connected


def uploads_root() -> Path:

    return Path(settings.DATA_DIR) / "uploads"


def user_upload_dir(user_id, create: bool = False) -> Path:

    path = uploads_root() / str(user_id)

    if create:
        path.mkdir(parents=True, exist_ok=True)

    return path


def user_local_bases(db: Session, user_id) -> list[Path]:
    """Resolved directories this user may read from: registered folders + uploads."""

    bases = []

    for folder in get_local_folders(db, user_id):
        try:
            resolved = Path(folder.folder_path).resolve(strict=True)
        except OSError:
            continue
        # Re-check stored rows: legacy rows (e.g. "C:/") predate validation.
        if resolved.is_dir() and is_allowed_folder(resolved):
            bases.append(resolved)

    try:
        uploads = user_upload_dir(user_id).resolve(strict=True)
        if uploads.is_dir():
            bases.append(uploads)
    except OSError:
        pass

    return bases


def resolve_user_file(db: Session, user_id, user_path: str) -> Path | None:
    """Resolve an absolute or relative path to an existing file the user owns."""

    resolved = resolve_in_any(user_local_bases(db, user_id), user_path)

    if resolved is None or not resolved.is_file():
        return None

    return resolved


def resolve_upload(user_id, filename: str) -> Path:
    """Resolve a file inside the user's upload dir (raises UnsafePathError)."""

    resolved = resolve_safe(user_upload_dir(user_id), filename)

    if not resolved.is_file():
        raise UnsafePathError("Not a file.")

    return resolved


def owns_local_path(bases: list[Path], path: str) -> bool:
    """Ownership test for search results.

    realpath (not abspath) so links, "..", and Windows 8.3 short names are
    resolved the same way the registered folders were.
    """

    if not path:
        return False

    try:
        absolute = Path(os.path.realpath(path))
    except (OSError, ValueError):
        return False

    return any(is_within(absolute, base) for base in bases)


def connected_platforms(db: Session, user_id) -> set:

    return {platform for platform in ("google_drive", "github") if is_platform_connected(db, user_id, platform)}
