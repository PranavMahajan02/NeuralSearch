from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ownership import connected_platforms, resolve_user_file
from app.platforms.registry import platform_manager


def open_result(db: Session, user_id, request):
    """Describe how the browser should open a search result.

    Nothing is opened on the server. Returns either
    {"type": "url", "url": ...} (Drive / GitHub, opened in a new tab) or
    {"type": "download", "url": "/files/local?path=..."} (local files).
    """

    platform_name = request.platform

    if platform_name == "local_storage":
        platform_name = "local"

    if platform_name == "local":

        resolved = resolve_user_file(db, user_id, request.path)

        if resolved is None:
            raise AppError(404, "File not found.")

        return {
            "type": "download",
            "url": "/files/local?" + urlencode({"path": str(resolved)}),
            "filename": resolved.name
        }

    if platform_name not in ("google_drive", "github"):
        raise AppError(400, "Unknown platform.")

    if platform_name not in connected_platforms(db, user_id):
        raise AppError(404, "File not found.")

    if platform_name == "google_drive" and not request.file_id:
        raise AppError(400, "file_id is required for Google Drive.")

    platform = platform_manager.get(platform_name)

    result = platform.open(
        request.path,
        request.file_id
    )

    if result.get("status") != "success" or not result.get("url"):
        raise AppError(404, result.get("message") or "File not found.")

    return {
        "type": "url",
        "url": result["url"]
    }
