from app.core.errors import AppError
from app.core.ownership import resolve_upload
from app.core.paths import UnsafePathError
from app.services.index_delete import remove_from_index


INDEX_FILES = (
    "index.pkl",
    "image_index.pkl",
    "audio_index.pkl",
    "video_index.pkl"
)


def delete_file(user_id, filename):
    """Delete a file from the user's own upload directory only."""

    try:
        file_path = resolve_upload(user_id, filename)
    except UnsafePathError:
        # 404 for anything outside the user's dir: do not reveal what exists.
        raise AppError(404, "File not found.")

    file_path.unlink()

    # TODO(phase-3): delete the file's vectors from Qdrant as well; today only
    # the pickle indexes are pruned (by basename), exactly as before.
    for index_file in INDEX_FILES:
        remove_from_index(
            index_file,
            file_path.name
        )

    return {
        "status": "success",
        "message": "File deleted successfully."
    }
