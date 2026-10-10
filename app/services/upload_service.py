from pathlib import Path

from app.config.file_types import AUDIOS, DOCUMENTS, IMAGES, VIDEOS
from app.core.config import settings
from app.core.errors import AppError
from app.core.ownership import user_upload_dir
from app.core.paths import UnsafePathError, safe_filename

ALLOWED_UPLOAD_EXTENSIONS = frozenset(ext.lower() for ext in DOCUMENTS + IMAGES + AUDIOS + VIDEOS)

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
        raise AppError(400, "Invalid file name.") from None

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
                    raise AppError(413, f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.")
                buffer.write(chunk)

        partial.rename(target)

    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return {"status": "uploaded", "filename": target.name, "path": str(target)}


def index_upload_in_background(user_id, file_path):
    """BackgroundTasks entry point: index the upload for its owner and log
    failures instead of raising into Starlette."""

    import logging

    from app.services.indexing_pipeline import index_local_file

    try:
        index_local_file(user_id, file_path)
    except Exception:
        logging.getLogger("cogniseek.upload").exception("Indexing the uploaded file failed")
