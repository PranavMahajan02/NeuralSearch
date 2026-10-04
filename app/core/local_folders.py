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

    if is_root(path):
        raise AppError(400, "A drive or filesystem root cannot be indexed.")

    if not is_allowed_folder(path):
        raise AppError(400, "Folder is outside the allowed locations.")

    return str(path)


def allowed_roots() -> list:

    roots = []

    for root in settings.allowed_local_roots_list:
        try:
            roots.append(Path(root).resolve(strict=True))
        except OSError:
            continue

    return roots


def is_root(path: Path) -> bool:

    return path == Path(path.anchor) or path.parent == path


def is_allowed_folder(path: Path) -> bool:
    """`path` must already be resolved. Also applied to rows stored before
    validation existed, so a legacy "C:/" row grants nothing."""

    return not is_root(path) and any(is_within(path, root) for root in allowed_roots())
