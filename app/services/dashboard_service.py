"""Per-user dashboard numbers, computed from the indexed_files ledger."""

from sqlalchemy import func

from app.database.db import SessionLocal
from app.database.local_storage_service import get_local_folders
from app.database.models import IndexedFile, PlatformConnection


PLATFORMS = ("local", "google_drive", "github")

TYPES = ("document", "image", "audio", "video")


def _platform_detail(platform, by_platform, last_by_platform):

    last = last_by_platform.get(platform)

    return {"indexed_files": by_platform.get(platform, 0),
            "last_indexed_at": last.isoformat() + "Z" if last else None}


def get_dashboard_stats(user_id):

    with SessionLocal() as db:

        rows = (
            db.query(IndexedFile.platform, IndexedFile.file_type, IndexedFile.status, func.count())
            .filter(IndexedFile.user_id == user_id)
            .group_by(IndexedFile.platform, IndexedFile.file_type, IndexedFile.status)
            .all()
        )

        last_indexed = (
            db.query(func.max(IndexedFile.indexed_at))
            .filter(IndexedFile.user_id == user_id, IndexedFile.status == "indexed")
            .scalar()
        )

        last_by_platform = dict(
            db.query(IndexedFile.platform, func.max(IndexedFile.indexed_at))
            .filter(IndexedFile.user_id == user_id, IndexedFile.status == "indexed")
            .group_by(IndexedFile.platform)
            .all()
        )

        connections = {
            row.platform
            for row in db.query(PlatformConnection.platform).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.connected.is_(True)
            )
        }

        folders = [folder.folder_path for folder in get_local_folders(db, user_id)]

    by_type = {file_type: 0 for file_type in TYPES}
    by_platform = {platform: 0 for platform in PLATFORMS}
    by_status = {"indexed": 0, "no_content": 0, "failed": 0, "unsupported": 0, "too_large": 0, "excluded": 0}

    for platform, file_type, status, count in rows:
        by_status[status] = by_status.get(status, 0) + count
        if status == "indexed":
            by_type[file_type] = by_type.get(file_type, 0) + count
            by_platform[platform] = by_platform.get(platform, 0) + count

    connected = len(connections & {"google_drive", "github"}) + (1 if folders else 0)

    return {
        "total_files": by_status["indexed"],
        "documents": by_type["document"],
        "images": by_type["image"],
        "audio": by_type["audio"],
        "video": by_type["video"],
        "by_platform": by_platform,
        "no_content_files": by_status["no_content"],
        "failed_files": by_status["failed"],
        "last_indexed_at": last_indexed,
        "connected_platforms": connected,
        "ready_platforms": sum(1 for count in by_platform.values() if count > 0),
        "supported_platforms": len(PLATFORMS),
        "platforms": {
            "google_drive": {"connected": "google_drive" in connections,
                             **_platform_detail("google_drive", by_platform, last_by_platform)},
            "github": {"connected": "github" in connections,
                       **_platform_detail("github", by_platform, last_by_platform)},
            "local": {"connected": len(folders) > 0, "folders": folders,
                      **_platform_detail("local", by_platform, last_by_platform)}
        }
    }


def get_recent_files(user_id, limit: int = 8):
    """The last `limit` files indexed for this user (newest first)."""

    with SessionLocal() as db:
        rows = (
            db.query(IndexedFile)
            .filter(IndexedFile.user_id == user_id, IndexedFile.status == "indexed")
            .order_by(IndexedFile.indexed_at.desc())
            .limit(limit)
            .all()
        )

    return [
        {
            "platform": row.platform,
            "source_id": row.source_id,
            "file": row.file_name,
            "display_path": row.display_path,
            "type": row.file_type,
            "indexed_at": row.indexed_at.isoformat() + "Z" if row.indexed_at else None,
        }
        for row in rows
    ]


def get_dashboard_platforms(user_id):

    return get_dashboard_stats(user_id)["platforms"]
