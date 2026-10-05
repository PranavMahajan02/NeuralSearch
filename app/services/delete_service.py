from app.core.errors import AppError
from app.core.ownership import resolve_upload
from app.core.paths import UnsafePathError
from app.services import index_store
from app.services.indexing_pipeline import local_source_id


def delete_file(user_id, filename):
    """Delete a file from the user's own upload directory and from the index."""

    try:
        file_path = resolve_upload(user_id, filename)
    except UnsafePathError:
        # 404 for anything outside the user's dir: do not reveal what exists.
        raise AppError(404, "File not found.")

    source_id = local_source_id(str(file_path))

    file_path.unlink()

    # Vectors in every collection + the ledger row, for this user only.
    index_store.delete_file(user_id, "local", source_id)

    return {
        "status": "success",
        "message": "File deleted successfully."
    }
