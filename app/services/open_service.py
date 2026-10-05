from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ownership import resolve_user_file
from app.services import index_store
from app.services.indexing_pipeline import local_source_id


def _owned_source(user_id, platform: str, source_id):
    """The user's ledger row for this source, or 404 (also for other users')."""

    row = index_store.get_source(user_id, platform, source_id) if source_id else None

    if row is None:
        raise AppError(404, "File not found.")

    return row


def drive_url(file_id: str) -> str:

    return f"https://drive.google.com/file/d/{quote(file_id, safe='')}/view"


def github_url(owner: str, repo: str, path: str, branch: str = None) -> str:
    """Blob URL on the repository's default branch (stored at index time)."""

    return f"https://github.com/{quote(owner)}/{quote(repo)}/blob/{quote(branch or 'main', safe='')}/{quote(path)}"


def open_result(db: Session, user_id, request):
    """Describe how the browser should open a search result.

    Nothing is opened on the server. The source must be in this user's
    indexed_files ledger, otherwise 404 (same answer whether it does not
    exist or belongs to someone else).
    """

    platform = "local" if request.platform == "local_storage" else request.platform

    if platform == "local":

        source_id = request.source_id or (local_source_id(request.path) if request.path else None)
        row = _owned_source(user_id, "local", source_id)

        resolved = resolve_user_file(db, user_id, row.display_path)

        if resolved is None:
            raise AppError(404, "File not found.")

        return {
            "type": "download",
            "url": "/files/local?" + urlencode({"path": str(resolved)}),
            "filename": resolved.name
        }

    if platform == "google_drive":

        row = _owned_source(user_id, "google_drive", request.source_id or request.file_id)

        # The webViewLink stored at index time (works for native Google files too).
        return {"type": "url", "url": row.web_view_link or drive_url(row.source_id)}

    if platform == "github":

        row = _owned_source(user_id, "github", request.source_id)
        path = row.source_id.split(":", 1)[1]

        return {"type": "url", "url": github_url(row.owner, row.repo, path, row.default_branch)}

    raise AppError(400, "Unknown platform.")
