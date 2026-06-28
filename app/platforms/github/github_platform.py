import os

from app.platforms.base_platform import BasePlatform
from app.services.upload_service import process_uploaded_file

from app.platforms.github.github_service import (
    list_repositories,
    get_all_files,
    download_file
)


SUPPORTED_EXTENSIONS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
)


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

                extension = os.path.splitext(
                    file["name"]
                )[1].lower()

                if extension not in SUPPORTED_EXTENSIONS:
                    continue

                print(f"Downloading: {file['path']}")

                path = download_file(file)

                if path is None:
                    continue

                process_uploaded_file(
                    path,
                    platform="github",
                    file_id=file["path"],
                    file_sha=file["sha"],
                    owner=owner,
                    repo=repo_name
                )

                if os.path.exists(path):
                    os.remove(path)

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

        return results    

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