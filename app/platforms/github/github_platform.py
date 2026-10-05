import os

from app.platforms.base_platform import BasePlatform
from app.platforms.errors import PlatformPreconditionError
from app.platforms.indexing import is_supported, process_files
from app.services.indexing_pipeline import github_meta, index_source
from app.database.db import SessionLocal

from app.platforms.github.github_service import (
    list_repositories,
    get_all_files,
    download_file
)


SKIP_FOLDERS = {
    "temp",
    "temp_frames",
    ".git",
    "__pycache__",
    "venv",
    "node_modules",
    ".idx",
    "build",
    "dist"
}


def is_github_file_supported(file: dict) -> bool:

    if file.get("download_url") is None:
        return False

    if any(part in SKIP_FOLDERS for part in file["path"].split("/")):
        return False

    return is_supported(file["path"])


class GitHubPlatform(BasePlatform):

    def index(self, ctx):

        with SessionLocal() as db:

            # Not connected / bad token / rate limit -> PlatformPreconditionError.
            repos = list_repositories(db, ctx.user_id)

            supported = []
            skipped = 0

            # One listing pass per repo (the old code listed every repo twice).
            for repo in repos:

                if ctx.is_cancelled():
                    break

                owner = repo["owner"]["login"]
                repo_name = repo["name"]

                try:
                    files = get_all_files(db, ctx.user_id, owner, repo_name)
                except Exception as error:
                    # e.g. an empty repo (409) or a repo we may not read (403).
                    if isinstance(error, PlatformPreconditionError):
                        raise
                    ctx.record_error(f"{owner}/{repo_name}", error)
                    continue

                for file in files:
                    if is_github_file_supported(file):
                        supported.append((owner, repo_name, file))
                    else:
                        skipped += 1

            ctx.add_skipped(skipped)
            ctx.set_total(len(supported))

            def handle(position, item):

                owner, repo_name, file = item

                local_path = download_file(
                    db,
                    ctx.user_id,
                    file,
                    download_folder=str(ctx.file_dir(position))
                )

                try:
                    index_source(
                        github_meta(ctx.user_id, owner, repo_name, file),
                        local_path,
                        temp_dir=ctx.temp_dir
                    )
                finally:
                    try:
                        if local_path and os.path.exists(local_path):
                            os.remove(local_path)
                    except OSError:
                        pass  # the job temp dir is removed by the worker anyway

            process_files(
                ctx,
                supported,
                file_ref=lambda item: f"{item[0]}/{item[1]}:{item[2]['path']}",
                handle=handle
            )

            # TODO(phase-5): deletion sync (remove_deleted_github_files is broken).

    def list_files(self):

        return []