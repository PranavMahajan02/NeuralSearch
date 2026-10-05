import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.database.db import get_db
from app.database.platform_connection_service import get_platform_connection
from app.platforms.google_drive import oauth as google_oauth
from app.platforms.google_drive.drive_service import revoke_token
from app.platforms.google_drive.google_drive_credentials import (
    disconnect_google_credentials,
    save_google_credentials,
)
from app.platforms.oauth_state import InvalidOAuthState, consume_oauth_state_row, create_oauth_state
from app.services.index_store import purge_platform


logger = logging.getLogger("cogniseek.google_drive")


router = APIRouter(
    prefix="/platforms/google-drive",
    tags=["Google Drive"]
)


def _frontend_redirect(**params) -> RedirectResponse:

    return RedirectResponse(f"{settings.FRONTEND_URL}/?{urlencode(params)}", status_code=303)


def _connection(db: Session, user_id):

    connection = get_platform_connection(db, user_id, "google_drive")

    return connection if connection is not None and connection.connected else None


@router.get("/connect")
def connect_google_drive(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    connection = _connection(db, current_user["id"])

    if connection is not None:
        return {
            "status": "success",
            "connected": True,
            "account_email": connection.account_email,
            "message": "Google Drive already connected."
        }

    try:
        flow = google_oauth.build_flow()
    except (OSError, ValueError):
        logger.exception("Google OAuth client configuration is missing or invalid")
        raise AppError(503, "Google Drive is not configured on the server.")

    # Single-use state bound to this user; the PKCE verifier stays server-side.
    state = create_oauth_state(db, current_user["id"], "google_drive", code_verifier=flow.code_verifier)

    return {
        "status": "success",
        "connected": False,
        "authorization_url": google_oauth.authorization_url(state, flow)
    }


@router.get("/callback")
def google_drive_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):

    try:
        user_id, code_verifier = consume_oauth_state_row(db, state, "google_drive")
    except InvalidOAuthState as e:
        return _frontend_redirect(google_drive="error", reason=e.code)

    if error or not code:
        return _frontend_redirect(google_drive="error", reason="access_denied")

    try:
        credentials = google_oauth.exchange_code(code, code_verifier)

        if not credentials.refresh_token:
            logger.warning("Google returned no refresh token; indexing will stop working when it expires")

        save_google_credentials(
            db,
            user_id,
            credentials,
            account_email=google_oauth.account_email(credentials)
        )

    except Exception:
        logger.exception("Google Drive OAuth callback failed")
        return _frontend_redirect(google_drive="error", reason="token_exchange_failed")

    return _frontend_redirect(google_drive="connected")


@router.get("/status")
def google_drive_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    connection = _connection(db, current_user["id"])

    return {
        "connected": connection is not None,
        "account_email": connection.account_email if connection else None
    }


@router.post("/disconnect")
def disconnect_google_drive(
    current_user=Depends(get_current_user),
    purge: bool = False,
    db: Session = Depends(get_db)
):

    connection = get_platform_connection(db, current_user["id"], "google_drive")
    revoked = None

    # Revoke at Google first; disconnect locally even if that fails.
    if connection is not None and (connection.refresh_token or connection.access_token):
        revoked = revoke_token(connection.refresh_token or connection.access_token)
        if not revoked:
            logger.warning("Google revoke failed for user %s; disconnecting locally anyway", current_user["id"])

    disconnect_google_credentials(db, current_user["id"])

    # ?purge=true also removes every indexed Drive file (this user only).
    purged = purge_platform(current_user["id"], "google_drive") if purge else 0

    return {
        "status": "success",
        "connected": False,
        "revoked": revoked,
        "purged_files": purged,
        "message": "Google Drive disconnected successfully."
    }
