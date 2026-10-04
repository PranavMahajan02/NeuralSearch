import os

from app.services.indexers.index_file import index_file
from app.services.index_manager import (
    is_file_indexed,
    is_file_modified,
    remove_file_from_index
)

from pathlib import Path

from app.config.file_types import AUDIOS, DOCUMENTS, IMAGES, VIDEOS
from app.core.config import settings
from app.core.errors import AppError
from app.core.ownership import user_upload_dir
from app.core.paths import UnsafePathError, safe_filename


ALLOWED_UPLOAD_EXTENSIONS = frozenset(
    ext.lower() for ext in DOCUMENTS + IMAGES + AUDIOS + VIDEOS
)

CHUNK_SIZE = 1024 * 1024


def _unique_path(directory: Path, filename: str) -> Path:
    """name.ext, name (1).ext, name (2).ext, ..."""

    candidate = directory / filename
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1

    while candidate.exists():
        candidate = directory / f"{stem} ({counter}){suffix}"
        counter += 1

    return candidate


def save_uploaded_file(file, user_id):
    """Validate and stream an upload into DATA_DIR/uploads/<user_id>/."""

    try:
        filename = safe_filename(file.filename)
    except UnsafePathError:
        raise AppError(400, "Invalid file name.")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise AppError(415, f"File type '{extension or 'none'}' is not allowed.")

    directory = user_upload_dir(user_id, create=True)
    target = _unique_path(directory, filename)
    partial = target.with_name(target.name + ".part")
    limit = settings.max_upload_bytes
    written = 0

    try:
        with open(partial, "xb") as buffer:
            while chunk := file.file.read(CHUNK_SIZE):
                written += len(chunk)
                if written > limit:
                    raise AppError(
                        413,
                        f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit."
                    )
                buffer.write(chunk)

        partial.rename(target)

    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return {
        "status": "uploaded",
        "filename": target.name,
        "path": str(target)
    }


def process_uploaded_file(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    print("Checking:", file_path)

    indexed = is_file_indexed(
        file_path,
        platform=platform,
        file_id=file_id
    )

    if indexed:

        modified = is_file_modified(
            file_path,
            platform=platform,
            file_id=file_id,
            file_sha=file_sha
        )

        if not modified:

            print("Already indexed. No changes detected.")
            return

        print("File modified. Re-indexing...")
        
        remove_file_from_index(
            file_path,
            platform=platform,
            file_id=file_id
        )

    else:

        print("New file. Indexing...")

    try:

        index_file(
            file_path,
            platform=platform,
            file_id=file_id,
            file_sha=file_sha,
            owner=owner,
            repo=repo
        )

    except Exception as e:

        print(f"Failed to index {file_path}")

        print(e)