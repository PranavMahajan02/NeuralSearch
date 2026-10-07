"""GitHub connector: repositories -> git trees -> changed blobs -> index."""

import logging
import os
from pathlib import PurePosixPath
from typing import List, Optional

from app.core.config import settings
from app.database.db import SessionLocal
from app.platforms.base_platform import BasePlatform
from app.platforms.errors import PlatformPreconditionError
from app.platforms.github.github_service import GitHubClient, TreeEntry
from app.platforms.sync import RemoteFile, sync_remote


logger = logging.getLogger("cogniseek.github")


# Vendored / generated paths are never indexed (and drop out of the index).
SKIP_DIRECTORIES = {
    "node_modules", "dist", "build", ".git", "venv", ".venv", "env", "__pycache__",
    "vendor", "bower_components", ".next", ".idea", ".vscode", "temp", "temp_frames",
}

LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock",
    "cargo.lock", "composer.lock", "gemfile.lock", "go.sum",
}

LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/"
LFS_POINTER_MAX_BYTES = 1024


def is_vendored(path: str) -> bool:

    parts = PurePosixPath(path).parts
    name = parts[-1].lower() if parts else ""

    return (
        any(part.lower() in SKIP_DIRECTORIES for part in parts[:-1])
        or name in LOCK_FILES
        or name.endswith((".min.js", ".min.css", ".map"))
    )


def is_lfs_pointer(content: bytes) -> bool:

    return len(content) <= LFS_POINTER_MAX_BYTES and content.startswith(LFS_POINTER_PREFIX)


def include_repository(repo: dict) -> bool:

    if repo.get("fork") and not settings.GITHUB_INCLUDE_FORKS:
        return False

    if repo.get("archived") and not settings.GITHUB_INCLUDE_ARCHIVED:
        return False

    return True


class GitHubPlatform(BasePlatform):

    def __init__(self, client: Optional[GitHubClient] = None):

        self._client = client

    def _make_client(self, user_id) -> GitHubClient:

        if self._client is not None:
            return self._client

        from app.platforms.github.oauth import get_access_token

        with SessionLocal() as db:
            token = get_access_token(db, user_id)      # PlatformPreconditionError if not connected

        return GitHubClient(token, user_id=user_id)

    def index(self, ctx):

        from app.services.indexing_pipeline import github_meta

        client = self._make_client(ctx.user_id)

        remote_files: List[RemoteFile] = []
        complete = True

        repos = [repo for repo in client.iter_repositories() if include_repository(repo)]

        for repo in repos:

            if ctx.is_cancelled():
                return

            owner = repo["owner"]["login"]
            name = repo["name"]
            branch = repo.get("default_branch") or "main"

            try:
                entries, repo_complete = client.tree(owner, name, branch)
            except PlatformPreconditionError:
                raise
            except Exception as error:
                # One repository failing must not wipe its files from the
                # index: mark the whole listing incomplete.
                ctx.record_error(f"{owner}/{name}", error)
                complete = False
                continue

            complete = complete and repo_complete

            for entry in entries:

                if is_vendored(entry.path):
                    continue

                meta = github_meta(
                    ctx.user_id, owner, name,
                    {"path": entry.path, "sha": entry.sha},
                    default_branch=branch
                )

                remote_files.append(RemoteFile(
                    meta=meta,
                    extension=os.path.splitext(entry.path)[1],
                    size=entry.size,
                    download=self._downloader(client, owner, name, entry)
                ))

        sync_remote(ctx, "github", remote_files, listing_complete=complete)

    @staticmethod
    def _downloader(client: GitHubClient, owner: str, repo: str, entry: TreeEntry):

        def download(target):
            content = client.blob(owner, repo, entry.sha)
            if is_lfs_pointer(content):
                return None                 # the real file lives in Git LFS
            target.write_bytes(content)
            return str(target)

        return download

    def list_files(self):

        return []
