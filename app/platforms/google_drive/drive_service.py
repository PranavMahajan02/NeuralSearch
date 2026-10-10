"""Google Drive API client for the connector.

- one Drive client per job (not per file)
- every API call is retried on 429/5xx (app.platforms.http)
- tokens: refreshed when needed; a refreshed token is saved back (encrypted);
  invalid_grant -> the connection is marked disconnected and the job fails
  with "Google authorization expired - reconnect"
"""

import io
import json
import logging
import threading
from pathlib import Path

from app.database.db import SessionLocal
from app.database.platform_connection_service import (
    disconnect_platform,
    get_platform_connection,
)
from app.platforms import http
from app.platforms.errors import PlatformPreconditionError

logger = logging.getLogger("cogniseek.google_drive")

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

SCOPES = [
    DRIVE_SCOPE,
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."

# Google-native types we can export, and to what.
EXPORTS = {
    "application/vnd.google-apps.document":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.presentation":
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.spreadsheet":
        ("text/csv", ".csv"),
}

LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, modifiedTime, size, md5Checksum, "
    "webViewLink, shortcutDetails)"
)


class GoogleAuthExpired(PlatformPreconditionError):

    def __init__(self):

        super().__init__("Google authorization expired — reconnect Google Drive.")


class GoogleDrivePermissionMissing(PlatformPreconditionError):

    def __init__(self):

        super().__init__("Google Drive permission missing — reconnect and allow Drive access.")


# 403 reasons that mean "this token may not read Drive" (not a transient error).
PERMISSION_REASONS = ("insufficientPermissions", "insufficientScopes", "ACCESS_TOKEN_SCOPE_INSUFFICIENT")


def is_permission_error(error: Exception) -> bool:

    if http_status(error) != 403:
        return False

    content = getattr(error, "content", b"") or b""
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else str(content)

    return any(reason in text or reason in str(error) for reason in PERMISSION_REASONS)


def http_status(error: Exception) -> int | None:

    status = getattr(getattr(error, "resp", None), "status", None)

    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def http_headers(error: Exception) -> dict:

    resp = getattr(error, "resp", None)

    try:
        return dict(resp) if resp is not None else {}
    except (TypeError, ValueError):
        return {}


# Token-endpoint errors that only a new consent can fix.
REAUTH_ERRORS = ("invalid_grant", "invalid_scope", "unauthorized_client")


def is_invalid_grant(error: Exception) -> bool:

    return any(code in str(error) for code in REAUTH_ERRORS)


def _mark_disconnected(user_id) -> None:

    with SessionLocal() as db:
        disconnect_platform(db, user_id, "google_drive")

    logger.warning("Google refused the stored credentials: Drive marked disconnected for user %s", user_id)


def load_credentials(user_id):

    from google.oauth2.credentials import Credentials

    with SessionLocal() as db:
        connection = get_platform_connection(db, user_id, "google_drive")

        if connection is None or not connection.connected or not connection.token_json:
            raise PlatformPreconditionError("Google Drive is not connected.")

        token_json = connection.token_json

    info = json.loads(token_json)

    # Use the scopes the token was actually granted: asking for more on a
    # refresh (e.g. a token from before openid/email were added) is rejected
    # with invalid_scope.
    return Credentials.from_authorized_user_info(info, info.get("scopes") or SCOPES)


def persist_credentials(user_id, credentials) -> None:
    """Save refreshed credentials back to the DB (encrypted at rest)."""

    with SessionLocal() as db:
        connection = get_platform_connection(db, user_id, "google_drive")

        if connection is None:
            return

        connection.token_json = credentials.to_json()
        connection.access_token = credentials.token

        if credentials.refresh_token:
            connection.refresh_token = credentials.refresh_token

        db.commit()


class DriveClient:
    """Drive API access for one user. Shared by the job's parallel download
    workers, so every thread gets its OWN authorized HTTP transport:
    httplib2.Http is not thread-safe, and two threads on one connection corrupt
    its TLS stream (SSL "bad record mac" / "wrong version number"). The
    credentials object is shared; a refreshed token is persisted once, under a lock."""

    def __init__(self, user_id, credentials, service=None, http_factory=None):

        self.user_id = user_id
        self.credentials = credentials
        self._saved_token = getattr(credentials, "token", None)
        self._save_lock = threading.Lock()
        self._local = threading.local()
        self._http_factory = http_factory

        self.ensure_fresh()

        if service is None:
            from googleapiclient.discovery import build
            service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        self.service = service

    # ------------------------------------------------------------------

    def ensure_fresh(self) -> None:

        creds = self.credentials

        if getattr(creds, "valid", True) or not getattr(creds, "refresh_token", None):
            return

        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request

        try:
            creds.refresh(Request())
        except RefreshError as error:
            if is_invalid_grant(error):
                _mark_disconnected(self.user_id)
                raise GoogleAuthExpired() from error
            raise

        self.save_if_refreshed()

    def save_if_refreshed(self) -> None:

        with self._save_lock:
            token = getattr(self.credentials, "token", None)

            if token and token != self._saved_token:
                persist_credentials(self.user_id, self.credentials)
                self._saved_token = token
                logger.info("Saved refreshed Google credentials for user %s", self.user_id)

    # ------------------------------------------------------------------
    # Per-thread transport
    # ------------------------------------------------------------------

    def _new_http(self):

        if self._http_factory is not None:
            return self._http_factory()

        import google_auth_httplib2
        import httplib2

        return google_auth_httplib2.AuthorizedHttp(self.credentials, http=httplib2.Http(timeout=60))

    def thread_http(self):
        """This thread's authorized transport (created on first use)."""

        transport = getattr(self._local, "http", None)
        if transport is None:
            transport = self._new_http()
            self._local.http = transport
        return transport

    def reset_thread_http(self, _error=None) -> None:
        """Drop this thread's transport (after a TLS / connection error)."""

        self._local.http = None

    def _call(self, request_factory):
        """Execute a googleapiclient request with retries and auth handling."""

        from google.auth.exceptions import RefreshError

        try:
            result = http.call_with_retry(
                lambda: request_factory().execute(http=self.thread_http()),
                http_status, http_headers, on_retry=self.reset_thread_http)
        except RefreshError as error:
            if is_invalid_grant(error):
                _mark_disconnected(self.user_id)
                raise GoogleAuthExpired() from error
            raise
        except Exception as error:
            self._raise_auth_problem(error)
            raise

        self.save_if_refreshed()

        return result

    def _raise_auth_problem(self, error: Exception) -> None:
        """401 -> expired; 403 insufficient permissions/scopes -> missing
        Drive permission. Both mark the connection disconnected."""

        if http_status(error) == 401:
            _mark_disconnected(self.user_id)
            raise GoogleAuthExpired() from error

        if is_permission_error(error):
            _mark_disconnected(self.user_id)
            raise GoogleDrivePermissionMissing() from error

    # ------------------------------------------------------------------

    def list_files(self) -> tuple[list[dict], bool]:
        """(all non-trashed files, complete). Paginates with pageSize=1000."""

        files: list[dict] = []
        page_token = None

        while True:
            response = self._call(lambda token=page_token: self.service.files().list(
                q="trashed=false",
                pageSize=1000,
                pageToken=token,
                fields=LIST_FIELDS,
                supportsAllDrives=False,
            ))
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return files, True

    def download(self, file: dict, target: Path) -> str:
        """Download (or export) one file to `target`; returns the path."""

        from googleapiclient.http import MediaIoBaseDownload

        export = EXPORTS.get(file.get("mimeType"))

        if export:
            request = self.service.files().export_media(fileId=file["id"], mimeType=export[0])
        else:
            request = self.service.files().get_media(fileId=file["id"])

        # MediaIoBaseDownload sends every chunk through request.http.
        request.http = self.thread_http()

        def fresh_connection(error):
            self.reset_thread_http(error)
            request.http = self.thread_http()

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False

        while not done:
            try:
                _status, done = http.call_with_retry(
                    lambda: downloader.next_chunk(), http_status, http_headers, on_retry=fresh_connection)
            except Exception as error:
                self._raise_auth_problem(error)
                raise

        target.write_bytes(buffer.getvalue())
        self.save_if_refreshed()

        return str(target)


def client_for_user(user_id) -> DriveClient:

    return DriveClient(user_id, load_credentials(user_id))


def revoke_token(token: str) -> bool:
    """Revoke at Google (https://oauth2.googleapis.com/revoke)."""

    try:
        response = http.request(
            "POST",
            "https://oauth2.googleapis.com/revoke",
            data={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            max_tries=2
        )
    except Exception as error:
        logger.warning("Google token revoke failed: %s", type(error).__name__)
        return False

    if response.status_code not in (200, 400):   # 400 = already invalid
        logger.warning("Google token revoke returned HTTP %s", response.status_code)
        return False

    return True
