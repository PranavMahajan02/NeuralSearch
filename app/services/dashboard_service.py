import os
import pickle
from app.scheduler.status import get_status
from app.database.db import SessionLocal
from app.database.local_storage_service import get_local_folders
from app.database.platform_connection_service import (
    is_platform_connected
)

def count_index(index_file):

    if not os.path.exists(index_file):
        return 0

    try:

        with open(index_file, "rb") as f:

            data = pickle.load(f)

    except (EOFError, pickle.UnpicklingError):

        # File is currently being rewritten.
        # Return 0 temporarily and let the next dashboard refresh succeed.

        return 0

    files = set()

    for item in data:

        files.add(
            (
                item.get("platform"),
                item.get("file")
            )
        )

    return len(files)

def get_dashboard_stats(user_id):

    documents = count_index("index.pkl")
    images = count_index("image_index.pkl")
    audio = count_index("audio_index.pkl")
    video = count_index("video_index.pkl")

    total = (
        documents
        + images
        + audio
        + video
    )

    scheduler = get_status()

    db = SessionLocal()

    try:

        drive_connected = is_platform_connected(
            db,
            user_id,
            "google_drive"
        )

        github_connected = is_platform_connected(
            db,
            user_id,
            "github"
        )

        folders = [

            folder.folder_path

            for folder in get_local_folders(
                db,
                user_id
            )

        ]

    finally:

        db.close()

    return {

        "total_files": total,

        "documents": documents,

        "images": images,

        "audio": audio,

        "video": video,

        "connected_platforms": len(
            scheduler["completed_platforms"]
        ),

        "ready_platforms": len(
            scheduler["completed_platforms"]
        ),

        "platforms": {

            "google_drive": {

                "connected": drive_connected

            },

            "github": {

                "connected": github_connected

            },

            "local": {

                "connected": len(folders) > 0,

                "folders": folders

            }

        }

    }

def get_dashboard_platforms(user_id):

    db = SessionLocal()

    try:

        drive = is_platform_connected(
            db,
            user_id,
            "google_drive"
        )

        github = is_platform_connected(
            db,
            user_id,
            "github"
        )

        folders = [

            folder.folder_path

            for folder in get_local_folders(
                db,
                user_id
            )

        ]

    finally:

        db.close()

    return {

        "google_drive": {

            "connected": drive

        },

        "github": {

            "connected": github

        },

        "local": {

            "connected": len(folders) > 0,

            "folders": folders

        }

    }