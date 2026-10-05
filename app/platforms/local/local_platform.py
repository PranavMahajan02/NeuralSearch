import os
from pathlib import Path

from app.platforms.base_platform import BasePlatform
from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import is_supported, process_files
from app.database.db import SessionLocal
from app.database.local_storage_service import get_local_folders


class LocalPlatform(BasePlatform):

    def __init__(self, folders=None):

        if folders is None:
            folders = []

        self.folders = folders

    def index(self, ctx):

        from app.core.local_folders import is_allowed_folder
        from app.services.upload_service import process_uploaded_file
        from app.services.index_manager import remove_deleted_files

        with SessionLocal() as db:
            stored = [folder.folder_path for folder in get_local_folders(db, ctx.user_id)]

        folders = []

        for raw in stored:
            try:
                resolved = Path(raw).resolve(strict=True)
            except OSError:
                ctx.record_error(raw, FileNotFoundError("Folder no longer exists."))
                continue
            # Same rules as registration (no roots, inside ALLOWED_LOCAL_ROOTS).
            if resolved.is_dir() and is_allowed_folder(resolved):
                folders.append(str(resolved))

        if not folders:
            raise PlatformPreconditionError("No valid local folders are registered.")

        self.folders = folders
        ctx.allowed_roots.extend(Path(folder) for folder in folders)

        # TODO(phase-3): prunes the global pickles; replaced by the per-user index.
        remove_deleted_files()

        supported, skipped = self.scan(folders)

        ctx.add_skipped(skipped)
        ctx.set_total(len(supported))

        process_files(
            ctx,
            supported,
            file_ref=lambda path: path,
            handle=lambda _position, path: process_uploaded_file(
                path,
                platform="local",
                temp_dir=ctx.temp_dir
            )
        )

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

        # Files are never opened on the server; the browser downloads them
        # through GET /files/local (see app/services/open_service.py).
        return {
            "status": "success",
            "path": file_path
        }

    def upload(self, file_path):

        print(f"Uploading: {file_path}")

    def delete(self, file_name):

        print(f"Deleting: {file_name}")

    @staticmethod
    def scan(folders):
        """(supported file paths, number of skipped entries).

        Skipped = sub-folders + unsupported files; they are not part of the
        progress denominator."""

        supported = []
        skipped = 0

        for folder in folders:

            if not os.path.isdir(folder):
                continue

            for root, dirnames, filenames in os.walk(folder):

                skipped += len(dirnames)

                for name in filenames:
                    if is_supported(name):
                        supported.append(os.path.join(root, name))
                    else:
                        skipped += 1

        return supported, skipped

    def list_files(self):

        return self.scan(self.folders)[0]
