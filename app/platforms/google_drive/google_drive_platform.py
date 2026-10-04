from importlib.metadata import files
import os
import webbrowser
from app.scheduler.cancel import is_cancelled, clear_cancel
from app.platforms.base_platform import BasePlatform
from app.platforms.google_drive.drive_service import (
    get_drive_service
)
from app.database.db import SessionLocal

from app.database.indexing_job_service import (
    set_total_files,
    increment_indexed_files,
    update_current_file
)


class GoogleDrivePlatform(BasePlatform):

    def index(
        self,
        user_id
    ):

        os.makedirs(
            "temp",
            exist_ok=True
        )

        from app.platforms.google_drive.drive_service import download_file
        from app.services.upload_service import process_uploaded_file

        files = self.list_files(
            user_id
        )
        print(f"\nFound {len(files)} Google Drive files.\n")

        db = SessionLocal()

        try:

            set_total_files(
                db,
                user_id,
                "google_drive",
                len(files)
            )

            for file in files:

                if is_cancelled(user_id):
                    print("\nGoogle Drive indexing cancelled.")
                    break

                name = file["name"]
                file_id = file["id"]
                mime = file["mimeType"]
                modified_time = file["modifiedTime"]

                # Skip folders
                if mime == "application/vnd.google-apps.folder":
                    print(f"Skipping folder: {name}")
                    continue

                temp_path = os.path.join(
                    "temp",
                    name
                )

                downloaded_path = None

                try:

                    print(f"\nDownloading: {name}")

                    print(f"Name: {name}")
                    print(f"MIME: {mime}")

                    downloaded_path = download_file(
                        user_id,
                        file_id,
                        temp_path,
                        mime
                    )

                    print(f"Indexing: {os.path.basename(downloaded_path)}")

                    update_current_file(
                        db,
                        user_id,
                        "google_drive",
                        name
                    )

                    process_uploaded_file(
                        downloaded_path,
                        platform="google_drive",
                        file_id=file_id,
                        file_sha=modified_time
                    )

                    increment_indexed_files(
                        db,
                        user_id,
                        "google_drive"
                    )

                    print(f"Finished: {name}")

                finally:

                    if (
                        downloaded_path
                        and os.path.exists(downloaded_path)
                    ):
                        os.remove(downloaded_path)

        finally:

            db.close()
            clear_cancel(user_id)
            print("\nGoogle Drive indexing completed.")

    def list_files(
        self,
        user_id
    ):

        service = get_drive_service(
            user_id
        )

        files = []
        page_token = None

        while True:

            response = service.files().list(
                q="trashed=false",
                pageSize=1000,
                pageToken=page_token,
                fields="nextPageToken, files(id,name,mimeType,modifiedTime)"
            ).execute()

            files.extend(response.get("files", []))

            page_token = response.get("nextPageToken")

            if page_token is None:
                break

        return files

    def search(
        self,
        query,
        search_type="all"
    ):

        print(f"Searching Google Drive: {query}")

        from app.services.document_service import search_document
        from app.services.image_service import search_image
        from app.services.audio_service import search_audio_file
        from app.services.video_service import search_video_file

        results = []

        if search_type == "all":

            results.extend(
                search_document(
                    query,
                    "google_drive"
                )
            )

            results.extend(
                search_image(
                    query,
                    "google_drive"
                )
            )

            results.extend(
                search_audio_file(
                    query,
                    "google_drive"
                )
            )

            results.extend(
                search_video_file(
                    query,
                    "google_drive"
                )
            )

        elif search_type == "document":

            results.extend(
                search_document(
                    query,
                    "google_drive"
                )
            )

        elif search_type == "image":

            results.extend(
                search_image(
                    query,
                    "google_drive"
                )
            )

        elif search_type == "audio":

            results.extend(
                search_audio_file(
                    query,
                    "google_drive"
                )
            )

        elif search_type == "video":

            results.extend(
                search_video_file(
                    query,
                    "google_drive"
                )
            )

        return results
        
    def open(
        self,
        file_path,
        file_id=None
    ):

        if not file_id:

            return {
               "status": "error",
               "message": "File ID not found."
            }

        url = f"https://drive.google.com/file/d/{file_id}/view"

        return {
            "status": "success",
            "url": url
        }

    def upload(self, file_path):

        print(f"Upload not implemented: {file_path}")

    def delete(self, file_name):

        print(f"Delete not implemented: {file_name}")