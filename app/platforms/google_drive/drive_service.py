import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.database.db import SessionLocal

from app.platforms.google_drive.google_drive_credentials import (
    load_google_credentials
)


def get_drive_service(user_id):

    db = SessionLocal()

    try:

        creds = load_google_credentials(

            db,

            user_id

        )

        if creds is None:

            raise Exception(

                "Google Drive is not connected."

            )

    finally:

        db.close()

    return build(

        "drive",

        "v3",

        credentials=creds

    )


def download_file(

    user_id,

    file_id,

    save_path,

    mime_type

):

    service = get_drive_service(

        user_id

    )

    # -----------------------------------
    # Google Docs
    # -----------------------------------

    if mime_type == "application/vnd.google-apps.document":

        request = service.files().export_media(

            fileId=file_id,

            mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        )

        save_path = os.path.splitext(save_path)[0] + ".docx"

    # -----------------------------------
    # Google Slides
    # -----------------------------------

    elif mime_type == "application/vnd.google-apps.presentation":

        request = service.files().export_media(

            fileId=file_id,

            mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation"

        )

        save_path = os.path.splitext(save_path)[0] + ".pptx"

    # -----------------------------------
    # Google Sheets
    # -----------------------------------

    elif mime_type == "application/vnd.google-apps.spreadsheet":

        request = service.files().export_media(

            fileId=file_id,

            mimeType="text/csv"

        )

        save_path = os.path.splitext(save_path)[0] + ".csv"

    # -----------------------------------
    # Normal Files
    # -----------------------------------

    else:

        request = service.files().get_media(

            fileId=file_id

        )

    with io.FileIO(

        save_path,

        "wb"

    ) as file:

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