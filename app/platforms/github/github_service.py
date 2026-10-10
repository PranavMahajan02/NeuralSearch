"""GitHub REST client for the connector.

- every call goes through app.platforms.http (retries, rate limits, timeouts)
- repositories: /user/repos, 100 per page, following the Link header (BUG-11)
- files: ONE recursive git-trees call per repository (path, blob sha, size);
  a truncated tree falls back to walking sub-trees
- 401 anywhere: the connection is marked disconnected and the job fails with
  "GitHub authorization expired - reconnect"
"""

import logging
import re
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

import requests

from app.database.db import SessionLocal
from app.database.platform_connection_service import disconnect_platform
from app.platforms import http
from app.platforms.errors import PlatformPreconditionError

logger = logging.getLogger("cogniseek.github")

API = "https://api.github.com"

_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class GitHubAuthExpired(PlatformPreconditionError):

    def __init__(self):

        super().__init__("GitHub authorization expired — reconnect GitHub.")


class GitHubPermissionMissing(PlatformPreconditionError):

    def __init__(self):

        super().__init__("GitHub permission missing — reconnect and allow repository access.")


class GitHubError(RuntimeError):
    """A non-fatal API error for one repository or file."""


@dataclass
class TreeEntry:

    path: str
    sha: str
    size: int | None


class GitHubClient:

    def __init__(self, token: str, user_id=None, session: requests.Session | None = None):

        self.user_id = user_id
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        # An injected session (tests) is used as-is; otherwise one Session per
        # thread: requests.Session is not documented as thread-safe, and the job
        # downloads files from several threads at once.
        self._injected = session
        if session is not None:
            session.headers.update(self._headers)
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:

        if self._injected is not None:
            return self._injected
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(self._headers)
            self._local.session = session
        return session

    # ------------------------------------------------------------------

    def _get(self, url: str, accept: str | None = None, allow: tuple[int, ...] = ()) -> requests.Response:

        headers = {"Accept": accept} if accept else None
        response = http.request("GET", url if url.startswith("http") else API + url, session=self.session, headers=headers)

        if response.status_code == 401:
            self._mark_disconnected()
            raise GitHubAuthExpired()

        # A token granted without the "repo" scope (X-OAuth-Scopes lists what
        # the token really has): not fixable by retrying.
        if response.status_code in (403, 404) and "X-OAuth-Scopes" in response.headers:
            granted = {s.strip() for s in response.headers["X-OAuth-Scopes"].split(",") if s.strip()}
            if "repo" not in granted:
                self._mark_disconnected()
                raise GitHubPermissionMissing()

        if response.status_code in allow:
            return response

        if response.status_code >= 400:
            raise GitHubError(f"GitHub API {response.status_code} for {url.split('?')[0]}")

        return response

    def _mark_disconnected(self) -> None:

        if self.user_id is None:
            return

        with SessionLocal() as db:
            disconnect_platform(db, self.user_id, "github")

        logger.warning("GitHub token rejected (401): connection marked disconnected for user %s", self.user_id)

    # ------------------------------------------------------------------

    def user(self) -> dict:

        return self._get("/user").json()

    def iter_repositories(self) -> Iterator[dict]:
        """Every repository the user can access, across all pages."""

        url = f"{API}/user/repos?per_page=100&affiliation=owner,collaborator,organization_member"

        while url:
            response = self._get(url)
            yield from response.json()
            match = _LINK_NEXT.search(response.headers.get("Link", ""))
            url = match.group(1) if match else None

    def tree(self, owner: str, repo: str, branch: str) -> tuple[list[TreeEntry], bool]:
        """(file entries, complete). An empty repository (409) is ([], True)."""

        base = f"/repos/{quote(owner)}/{quote(repo)}/git/trees/"
        response = self._get(base + quote(branch, safe="") + "?recursive=1", allow=(404, 409))

        if response.status_code == 409:
            return [], True

        if response.status_code == 404:
            raise GitHubError(f"Branch '{branch}' not found in {owner}/{repo}")

        data = response.json()

        if not data.get("truncated"):
            return _blobs(data.get("tree", [])), True

        logger.warning("Tree of %s/%s is truncated; walking sub-trees", owner, repo)

        try:
            return self._walk(base, data["sha"], prefix=""), True
        except GitHubAuthExpired:
            raise
        except Exception as error:
            logger.warning("Sub-tree walk of %s/%s failed (%s): listing incomplete", owner, repo, error)
            return _blobs(data.get("tree", [])), False

    def _walk(self, base: str, sha: str, prefix: str) -> list[TreeEntry]:

        data = self._get(base + sha).json()
        entries: list[TreeEntry] = []

        for item in data.get("tree", []):
            path = f"{prefix}{item['path']}"
            if item["type"] == "blob":
                entries.append(TreeEntry(path=path, sha=item["sha"], size=item.get("size")))
            elif item["type"] == "tree":
                entries.extend(self._walk(base, item["sha"], prefix=f"{path}/"))

        return entries

    def blob(self, owner: str, repo: str, sha: str) -> bytes:

        url = f"/repos/{quote(owner)}/{quote(repo)}/git/blobs/{sha}"

        return self._get(url, accept="application/vnd.github.raw+json").content


def _blobs(items) -> list[TreeEntry]:

    return [
        TreeEntry(path=item["path"], sha=item["sha"], size=item.get("size"))
        for item in items
        if item.get("type") == "blob"
    ]


def client_for_user(db, user_id) -> GitHubClient:

    from app.platforms.github.oauth import get_access_token

    return GitHubClient(get_access_token(db, user_id), user_id=user_id)


def get_user(db, user_id) -> dict:

    return client_for_user(db, user_id).user()
