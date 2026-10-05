import os
import re

from app.platforms.base_platform import BasePlatform
from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import is_supported, process_files
from app.platforms.google_drive.drive_service import (
    get_drive_service
)


FOLDER_MIME = "application/vnd.google-apps.folder"

# Native Google files that download_file exports to a supported format.
EXPORTABLE_MIMES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.spreadsheet",
}

_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_local_name(name: str) -> str:
    """Drive names may contain '/' or characters Windows rejects."""

    cleaned = _UNSAFE_NAME.sub("_", name or "").strip(" .")

    return (cleaned or "file")[:200]


def is_drive_file_supported(file: dict) -> bool:

    return file.get("mimeType") in EXPORTABLE_MIMES or is_supported(file.get("name", ""))


def is_auth_error(error: Exception) -> bool:

    status = getattr(getattr(error, "resp", None), "status", None)

    return status in (401, 403)


class GoogleDrivePlatform(BasePlatform):

    def index(self, ctx):

        from app.platforms.google_drive.drive_service import download_file
        from app.services.indexing_pipeline import drive_meta, index_source

        try:
            files = self.list_files(ctx.user_id)
        except PlatformPreconditionError:
            raise
        except Exception as error:
            if is_auth_error(error):
                raise PlatformPreconditionError(
                    "Google Drive rejected the stored credentials. Please reconnect Google Drive."
                ) from error
            raise

        supported = []
        skipped = 0

        for file in files:
            if file.get("mimeType") == FOLDER_MIME or not is_drive_file_supported(file):
                skipped += 1
            else:
                supported.append(file)

        ctx.add_skipped(skipped)
        ctx.set_total(len(supported))

        def handle(position, file):

            target = ctx.file_dir(position) / safe_local_name(file["name"])
            downloaded_path = None

            try:
                downloaded_path = download_file(
                    ctx.user_id,
                    file["id"],
                    str(target),
                    file["mimeType"]
                )

                # TODO(phase-5): check needs_index before downloading (BUG-05).
                index_source(
                    drive_meta(ctx.user_id, file, downloaded_path),
                    downloaded_path,
                    temp_dir=ctx.temp_dir
                )

            except Exception as error:
                if is_auth_error(error):
                    raise PlatformPreconditionError(
                        "Google Drive access was revoked during indexing."
                    ) from error
                raise

            finally:
                if downloaded_path and os.path.exists(downloaded_path):
                    os.remove(downloaded_path)

        process_files(
            ctx,
            supported,
            file_ref=lambda file: file.get("name") or file.get("id"),
            handle=handle
        )

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
