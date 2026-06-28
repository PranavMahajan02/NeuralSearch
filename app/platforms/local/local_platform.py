import os

from app.platforms.base_platform import BasePlatform
from app.config.local_config import load_local_folders


class LocalPlatform(BasePlatform):

    def __init__(self, folders=None):

        if folders is None:
            folders = []

        self.folders = folders

    def index(self):

        self.folders = load_local_folders()

        from app.services.upload_service import process_uploaded_file
        from app.services.index_manager import remove_deleted_files

        remove_deleted_files()

        files = self.list_files()

        print(f"\nFound {len(files)} files.\n")

        for file_path in files:

            print(f"Indexing: {file_path}")

            process_uploaded_file(
                file_path,
                platform="local"
            )

        print("\nLocal indexing completed.")

    def search(self, query):

        from app.services.document_service import search_document
        from app.services.image_service import search_image
        from app.services.audio_service import search_audio_file
        from app.services.video_service import search_video_file

        results = []

        results.extend(
            search_document(
                query,
                "local"
            )
        )

        results.extend(
            search_image(
                query,
                "local"
            )
        )

        results.extend(
            search_audio_file(
                query,
                "local"
            )
        )

        results.extend(
            search_video_file(
                query,
                "local"
            )
        )

        return results

    def open(
        self,
        file_path,
        file_id=None
    ):

        if not os.path.exists(file_path):

            return {
                "status": "error",
                "message": "File not found."
            }

        os.startfile(file_path)

        return {
            "status": "success",
            "message": "File opened."
        }

    def upload(self, file_path):
        print(f"Uploading: {file_path}")

    def delete(self, file_name):
        print(f"Deleting: {file_name}")

    def list_files(self):

        files = []

        for folder in self.folders:

            if not os.path.exists(folder):
                continue

            for root, _, filenames in os.walk(folder):

                for file in filenames:

                    files.append(
                        os.path.join(root, file)
                    )

        return files