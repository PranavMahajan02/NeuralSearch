"""Google Drive connector: list metadata -> changed files -> download/export -> index."""

import logging
import os
from collections.abc import Callable

from app.platforms.base_platform import BasePlatform
from app.platforms.google_drive.drive_service import (
    EXPORTS,
    FOLDER_MIME,
    GOOGLE_NATIVE_PREFIX,
    SHORTCUT_MIME,
    DriveClient,
    client_for_user,
)
from app.platforms.sync import RemoteFile, sync_remote

logger = logging.getLogger("cogniseek.google_drive")


def local_extension(file: dict) -> str | None:
    """Extension the file will have locally, or None when it can't be fetched
    (folders, shortcuts, non-exportable Google-native types)."""

    mime = file.get("mimeType", "")

    if mime in (FOLDER_MIME, SHORTCUT_MIME):
        return None

    if mime in EXPORTS:
        return EXPORTS[mime][1]

    if mime.startswith(GOOGLE_NATIVE_PREFIX):
        return None      # forms, sites, maps, drawings, ... can't be exported

    return os.path.splitext(file.get("name", ""))[1]


class GoogleDrivePlatform(BasePlatform):

    def __init__(self, client_factory: Callable[[object], DriveClient] | None = None):

        self._client_factory = client_factory or client_for_user

    def index(self, ctx):

        from app.services.indexing_pipeline import drive_meta

        client = self._client_factory(ctx.user_id)      # one client per job

        files, complete = client.list_files()

        remote_files = []
        not_fetchable = 0

        for file in files:

            extension = local_extension(file)

            if extension is None:
                not_fetchable += 1
                continue

            size = file.get("size")

            remote_files.append(RemoteFile(
                meta=drive_meta(ctx.user_id, file, extension),
                extension=extension,
                size=int(size) if size is not None else None,
                download=self._downloader(client, file)
            ))

        ctx.add_skipped(not_fetchable)

        sync_remote(ctx, "google_drive", remote_files, listing_complete=complete)

        client.save_if_refreshed()

    @staticmethod
    def _downloader(client: DriveClient, file: dict):

        return lambda target: client.download(file, target)

    def list_files(self, user_id):

        return client_for_user(user_id).list_files()[0]
