import os
from app.services.index_manager import (
    remove_deleted_github_files
)
from app.platforms.base_platform import BasePlatform
from app.services.upload_service import process_uploaded_file

from app.platforms.github.github_service import (
    list_repositories,
    get_all_files,
    download_file
)


SUPPORTED_EXTENSIONS = (

    # Documents
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv",

    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",

    # Audio
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",

    # Video
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",

    # Source Code
    ".py",
    ".java",
    ".js",
    ".ts",
    ".tsx",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".sql",
    ".sh"
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

    def index(self):

        print("Fetching repositories...")

        repos = list_repositories()

        print(f"Found {len(repos)} repositories.")

        for repo in repos:

            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            print(f"\nRepository: {repo_name}")

            files = get_all_files(
                owner,
                repo_name
            )

            print(f"Found {len(files)} files.")

            for file in files:

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

                local_path = download_file(file)

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

                if os.path.exists(local_path):
                    os.remove(local_path)

        print("\nChecking for deleted GitHub files...")

        remove_deleted_github_files()

        print("\nGitHub indexing completed.")

    def search(
        self,
        query
    ):
    
        from app.services.document_service import search_document
        from app.services.image_service import search_image
        from app.services.audio_service import search_audio_file
        from app.services.video_service import search_video_file

        results = []

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

    # Global sorting
        results.sort(
            key=lambda x: x["score", 0],
            reverse=True
        )
     
        # Remove duplicate files (keep highest score)
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