import os

from app.platforms.base_platform import BasePlatform
from app.scheduler.cancel import is_cancelled, clear_cancel
from app.database.db import SessionLocal
from app.database.local_storage_service import get_local_folders
from app.database.indexing_job_service import (
    set_total_files,
    increment_indexed_files,
    update_current_file
)



class LocalPlatform(BasePlatform):

    def __init__(self, folders=None):

        if folders is None:
            folders = []

        self.folders = folders

    def index(
        self,
        user_id
    ):

        db = SessionLocal()

        try:

            self.folders = [

                folder.folder_path

                for folder in get_local_folders(

                    db,

                    user_id

                )

            ]

            # ==========================
            # DEBUG
            # ==========================

            print("\n==============================")
            print("LOCAL STORAGE DEBUG")
            print("==============================")
            print("User ID:", user_id)
            print("Folders loaded from DB:")
            print(self.folders)
            print("==============================\n")

        finally:

            db.close()

        from app.services.upload_service import process_uploaded_file
        from app.services.index_manager import remove_deleted_files

        remove_deleted_files()

        files = self.list_files()

        print(f"\nFound {len(files)} files.\n")

        db = SessionLocal()

        try:

            set_total_files(
                db,
                user_id,
                "local",
                len(files)
            )

            for file_path in files:

                if is_cancelled(user_id):

                    print("\nLocal indexing cancelled.")

                    break

                try:

                    print(f"Indexing: {file_path}")

                    # Update currently processing file
                    update_current_file(
                        db,
                        user_id,
                        "local",
                        os.path.basename(file_path)
                    )

                    process_uploaded_file(
                        file_path,
                        platform="local"
                    )

                    increment_indexed_files(
                        db,
                        user_id,
                        "local"
                    )

                except Exception as e:

                    print(
                        f"Failed to index {file_path}: {e}"
                    )

        finally:

            db.close()

            clear_cancel(user_id)

        print("\nLocal indexing completed.")

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

        elif search_type == "document":

            results.extend(
                search_document(
                    query,
                    "local"
                )
            )

        elif search_type == "image":

            results.extend(
                search_image(
                    query,
                    "local"
                )
            )

        elif search_type == "audio":

            results.extend(
                search_audio_file(
                    query,
                    "local"
                )
            )

        elif search_type == "video":

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

        print("\n========== SCANNING FOLDERS ==========")

        for folder in self.folders:

            print("\nFolder:")
            print(folder)

            exists = os.path.exists(folder)

            print("Exists:", exists)

            if not exists:
                continue

            for root, _, filenames in os.walk(folder):

                print(f"Scanning: {root}")
                print(f"Files in folder: {len(filenames)}")

                for file in filenames:

                    full_path = os.path.join(root, file)

                    print(f"Checking: {full_path}")
                    print("Exists:", os.path.exists(full_path))

                    files.append(full_path)

        print("======================================\n")

        return files