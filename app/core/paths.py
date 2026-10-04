"""Path-safety helpers for every endpoint that touches the file system."""

import os
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote


class UnsafePathError(ValueError):
    """The requested path is missing, malformed, or outside the allowed base."""


def _decode(user_input: str) -> str:

    # Decode repeatedly so double-encoded traversal ("..%252f") is caught too.
    previous = None
    value = user_input

    for _ in range(5):
        if value == previous:
            break
        previous, value = value, unquote(value)

    return value


def resolve_safe(base: Path, user_input: str) -> Path:
    """Resolve `user_input` (relative to `base`, or absolute) and return it only
    if the real, symlink-resolved path exists and lies inside `base`.

    Raises UnsafePathError otherwise. Absolute paths, drive letters, UNC paths,
    "../" (plain or URL-encoded) and symlinks pointing outside `base` are all
    rejected unless their resolved target is inside `base`.
    """

    if not isinstance(user_input, str) or not user_input.strip():
        raise UnsafePathError("Empty path.")

    decoded = _decode(user_input)

    if "\x00" in decoded:
        raise UnsafePathError("Invalid path.")

    try:
        real_base = Path(base).resolve(strict=True)
        candidate = (real_base / decoded).resolve(strict=True)
    except (OSError, RuntimeError):
        raise UnsafePathError("Path not found.") from None

    if not is_within(candidate, real_base):
        raise UnsafePathError("Path is outside the allowed directory.")

    return candidate


def is_within(path: Path, base: Path) -> bool:
    """True when `path` equals `base` or is below it (both already resolved)."""

    path_n = os.path.normcase(str(path))
    base_n = os.path.normcase(str(base))

    try:
        return os.path.commonpath([path_n, base_n]) == base_n
    except ValueError:
        # Different drives on Windows.
        return False


def resolve_in_any(bases: Iterable[Path], user_input: str) -> Optional[Path]:
    """Return the resolved path if it is inside any of `bases`, else None."""

    for base in bases:
        try:
            return resolve_safe(base, user_input)
        except UnsafePathError:
            continue

    return None


def safe_filename(name: str) -> str:
    """Validate an uploaded file name: a bare basename with no separators,
    no traversal, no control characters and no Windows-reserved characters."""

    decoded = _decode(name or "").strip()

    if (
        not decoded
        or decoded in {".", ".."}
        or any(sep in decoded for sep in ("/", "\\"))
        or ":" in decoded
        or any(ord(ch) < 32 for ch in decoded)
        or any(ch in decoded for ch in '<>"|?*')
        or len(decoded) > 255
    ):
        raise UnsafePathError("Invalid file name.")

    return decoded
