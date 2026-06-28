import os
import webbrowser

from app.platforms.base_platform import BasePlatform
from app.platforms.google_drive.drive_service import (
    get_drive_service
)


class GoogleDrivePlatform(BasePlatform):

    def index(self):

        os.makedirs(
            "temp",
            exist_ok=True
        )

        from app.platforms.google_drive.drive_service import download_file
        from app.services.upload_service import process_uploaded_file

        files = self.list_files()

        print(f"\nFound {len(files)} Google Drive files.\n")

        for file in files:

            name = file["name"]
            file_id = file["id"]
            mime = file["mimeType"]

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

                downloaded_path = download_file(
                    file_id,
                    temp_path,
                    mime
                )

                print(f"Indexing: {os.path.basename(downloaded_path)}")

                process_uploaded_file(
                    downloaded_path,
                    platform="google_drive",
                    file_id=file_id
                )

                print(f"Finished: {name}")

            finally:

                if (
                    downloaded_path
                    and os.path.exists(downloaded_path)
                ):
                    os.remove(downloaded_path)

    def list_files(self):

        service = get_drive_service()

        results = service.files().list(
            pageSize=2,
            fields="files(id,name,mimeType)"
        ).execute()

        return results.get("files", [])

    def search(self, query):

        print(f"Searching Google Drive: {query}")

        from app.services.document_service import search_document
        from app.services.image_service import search_image
        from app.services.audio_service import search_audio_file
        from app.services.video_service import search_video_file

        results = []

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

        webbrowser.open(url)

        return {
            "status": "success",
            "message": "Google Drive file opened."
        }

    def upload(self, file_path):

        print(f"Upload not implemented: {file_path}")

    def delete(self, file_name):

        print(f"Delete not implemented: {file_name}")