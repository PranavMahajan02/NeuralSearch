import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.platforms.google_drive.auth import authenticate


def get_drive_service():

    creds = authenticate()

    return build(
        "drive",
        "v3",
        credentials=creds
    )


def download_file(file_id, save_path, mime_type):

    service = get_drive_service()

    # ----------------------------
    # Google Docs
    # ----------------------------

    if mime_type == "application/vnd.google-apps.document":

        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        save_path = os.path.splitext(save_path)[0] + ".docx"

    # ----------------------------
    # Google Slides
    # ----------------------------

    elif mime_type == "application/vnd.google-apps.presentation":

        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

        save_path = os.path.splitext(save_path)[0] + ".pptx"

    # ----------------------------
    # Google Sheets
    # ----------------------------

    elif mime_type == "application/vnd.google-apps.spreadsheet":

        request = service.files().export_media(
            fileId=file_id,
            mimeType="text/csv"
        )

        save_path = os.path.splitext(save_path)[0] + ".csv"

    # ----------------------------
    # Normal files
    # ----------------------------

    else:

        request = service.files().get_media(
            fileId=file_id
        )

    with io.FileIO(save_path, "wb") as file:

        downloader = MediaIoBaseDownload(
            file,
            request
        )

        done = False

        while not done:

            status, done = downloader.next_chunk()

            if status:

                print(
                    f"Download: {int(status.progress() * 100)}%"
                )

    return save_path