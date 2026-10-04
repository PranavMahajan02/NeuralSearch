import os
import time
from app.services.index_manager import (
    remove_deleted_github_files
)
from app.platforms.base_platform import BasePlatform
from app.services.upload_service import process_uploaded_file
from app.database.db import SessionLocal
from app.database.indexing_job_service import (
    set_total_files,
    increment_indexed_files,
    update_current_file
)
from app.scheduler.cancel import (
    is_cancelled,
    clear_cancel
)

from app.platforms.github.github_service import (
    list_repositories,
    get_all_files,
    download_file
)

from app.config.file_types import (
    DOCUMENTS,
    IMAGES,
    AUDIOS,
    VIDEOS
)

SUPPORTED_EXTENSIONS = (
    DOCUMENTS
    + IMAGES
    + AUDIOS
    + VIDEOS
)

SKIP_FOLDERS = {
    "temp",
    "temp_frames",
    ".git",
    "__pycache__",
    "venv",
    "node_modules",
    ".idx",
    "build",
    "dist"
}


class GitHubPlatform(BasePlatform):

    def index(
        self,
        user_id
    ):

        print("Fetching repositories...")

        db = SessionLocal()

        try:

            repos = list_repositories(
                db,
                user_id
            )

            print(f"Found {len(repos)} repositories.")

            total_files = 0

            for repo in repos:

                owner = repo["owner"]["login"]
                repo_name = repo["name"]

                repo_files = get_all_files(
                    db,
                    user_id,
                    owner,
                    repo_name
                )

                for file in repo_files:

                    if file["download_url"] is None:
                        continue

                    github_path = file["path"]

                    path_parts = github_path.split("/")

                    if any(folder in SKIP_FOLDERS for folder in path_parts):
                        continue

                    extension = os.path.splitext(github_path)[1].lower()

                    if extension not in SUPPORTED_EXTENSIONS:
                        continue

                    total_files += 1

            set_total_files(
                db,
                user_id,
                "github",
                total_files
            )

            for repo in repos:

                if is_cancelled(user_id):

                    print("\nGitHub indexing cancelled.")

                    break

                owner = repo["owner"]["login"]
                repo_name = repo["name"]

                print(f"\nRepository: {repo_name}")

                files = get_all_files(
                    db,
                    user_id,
                    owner,
                    repo_name
                )

                print(f"Found {len(files)} files.")

                for file in files:

                    if is_cancelled(user_id):

                        print("\nGitHub indexing cancelled.")

                        break

                    if file["download_url"] is None:
                        continue

                    github_path = file["path"]

                    path_parts = github_path.split("/")

                    if any(
                        folder in SKIP_FOLDERS
                        for folder in path_parts
                    ):
                        continue

                    extension = os.path.splitext(
                        github_path
                    )[1].lower()

                    if extension not in SUPPORTED_EXTENSIONS:
                        continue

                    print(f"Downloading: {github_path}")

                    update_current_file(
                        db,
                        user_id,
                        "github",
                        github_path
                    )

                    local_path = download_file(
                        db,
                        user_id,
                        file
                    )

                    if local_path is None:
                        continue

                    process_uploaded_file(
                        local_path,
                        platform="github",
                        file_id=github_path,
                        file_sha=file["sha"],
                        owner=owner,
                        repo=repo_name
                    )

                    increment_indexed_files(
                        db,
                        user_id,
                        "github"
                    )

                    time.sleep(0.2)

                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                    except PermissionError:
                        print(f"Could not delete temp file: {local_path}")

            # TODO:
            # Enable after GitHub migration is complete.
            # remove_deleted_github_files()

            print("\nGitHub indexing completed.")

        finally:

            db.close()
            clear_cancel(user_id)

    def search(
        self,
        query,
        search_type="all"
    ):

        from app.services.document_service import search_document
        from app.services.image_service import search_image
        from app.services.audio_service import search_audio_file
        from app.services.video_service import search_video_file

        results = []

        if search_type == "all":

            results.extend(
                search_document(
                    query,
                    "github"
                )
            )

            results.extend(
                search_image(
                    query,
                    "github"
                )
            )

            results.extend(
                search_audio_file(
                    query,
                    "github"
                )
            )

            results.extend(
                search_video_file(
                    query,
                    "github"
                )
            )

        elif search_type == "document":

            results.extend(
                search_document(
                    query,
                    "github"
                )
            )

        elif search_type == "image":

            results.extend(
                search_image(
                    query,
                    "github"
                )
            )

        elif search_type == "audio":

            results.extend(
                search_audio_file(
                    query,
                    "github"
                )
            )

        elif search_type == "video":

            results.extend(
                search_video_file(
                    query,
                    "github"
                )
            )

        # Global sorting
        results.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        # Remove duplicate files
        unique_results = []
        seen = set()

        for result in results:

            key = (
                result.get("platform"),
                result.get("file_id")
                or result.get("path")
            )

            if key in seen:
                continue

            seen.add(key)
            unique_results.append(result)

        return unique_results

    def open(
        self,
        path,    
        file_id=None
    ):

        from app.platforms.github.github_service import (
            get_github_file_url
        )

        from app.services.index_manager import load_index

        data = load_index(path)

        for item in data:

            if (
                item.get("platform") == "github"
                and item.get("file_id") == file_id
            ):

                url = get_github_file_url(
                    item["owner"],
                    item["repo"],
                    item["file_id"]
                )    

                return {
                    "status": "success",
                    "url": url
                }

        return {
            "status": "error",
            "message": "GitHub file not found."
        }

    def upload(
        self,
        file_path
    ):

        print("GitHub upload not implemented.")

    def delete(
        self,
        file_name
    ):

        print("GitHub delete not implemented.")

    def list_files(self):

        return []