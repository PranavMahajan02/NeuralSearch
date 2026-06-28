import os
import shutil

from app.services.indexers.index_file import index_file
from app.services.index_manager import (
    is_file_indexed,
    is_file_modified,
    remove_file_from_index
)

UPLOAD_FOLDER = "data"

DOCUMENTS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".csv",
    ".txt"
)

IMAGES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif"
)

AUDIOS = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac"
)

VIDEOS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
)


def save_uploaded_file(file):

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    if os.path.exists(file_path):
        print("Duplicate file detected.")
        return {
            "status": "duplicate",
            "path": file_path
        }

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    return {
        "status": "uploaded",
        "path": file_path
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