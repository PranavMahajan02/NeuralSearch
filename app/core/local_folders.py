"""Validation for user-registered local folders."""

import os
from pathlib import Path

from app.core.config import settings
from app.core.errors import AppError
from app.core.paths import is_within


def normalize_folder(raw: str) -> str:
    """Resolve without requiring existence (used for removal lookups)."""

    return str(Path(os.path.expanduser(raw.strip())).resolve(strict=False))


def validate_local_folder(raw: str) -> str:
    """Return the normalized folder path, or raise AppError(400).

    The folder must exist, be a directory, not be a drive/filesystem root, and
    lie inside one of settings.ALLOWED_LOCAL_ROOTS.
    """

    if not raw or not raw.strip() or "\x00" in raw:
        raise AppError(400, "Folder path is required.")

    try:
        path = Path(os.path.expanduser(raw.strip())).resolve(strict=True)
    except (OSError, RuntimeError):
        raise AppError(400, "Folder does not exist.")

    if not path.is_dir():
        raise AppError(400, "Path is not a folder.")

    if path == Path(path.anchor) or path.parent == path:
        raise AppError(400, "A drive or filesystem root cannot be indexed.")

    allowed = []

    for root in settings.allowed_local_roots_list:
        try:
            allowed.append(Path(root).resolve(strict=True))
        except OSError:
            continue

    if not any(is_within(path, root) for root in allowed):
        raise AppError(400, "Folder is outside the allowed locations.")

    return str(path)
