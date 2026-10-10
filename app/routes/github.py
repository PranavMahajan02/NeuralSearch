import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter, user_key
from app.database.db import get_db
from app.database.platform_connection_service import get_platform_connection
from app.models import response_models as rm
from app.platforms.github.github_credentials import disconnect_github, save_github_credentials
from app.platforms.github.github_service import GitHubClient, get_user
from app.platforms.github.oauth import (
    InvalidOAuthState,
    consume_oauth_state,
    create_oauth_state,
    exchange_code_for_token,
    get_authorization_url,
    is_connected,
    revoke_grant,
)
from app.services.index_store import purge_platform

logger = logging.getLogger("cogniseek.github")


router = APIRouter(
    prefix="/platforms/github",
    tags=["GitHub"]
)


def _frontend_redirect(**params) -> RedirectResponse:

    return RedirectResponse(
        f"{settings.FRONTEND_URL}/?{urlencode(params)}",
        status_code=303
    )


@router.get("/connect", response_model=rm.ConnectResponse, response_model_exclude_unset=True)
@limiter.limit(settings.OAUTH_RATE_LIMIT, key_func=user_key)
def connect_github(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if is_connected(
        db,
        current_user["id"]
    ):

        user = get_user(
            db,
            current_user["id"]
        )

        return {
            "status": "success",
            "connected": True,
            "username": user["login"],
            "message": "GitHub already connected."
        }

    # Random single-use state bound to this user in the DB (CSRF protection).
    state = create_oauth_state(
        db,
        current_user["id"],
        "github"
    )

    return {
        "status": "success",
        "connected": False,
        "authorization_url": get_authorization_url(state)
    }


@router.get("/callback")
@limiter.limit(settings.OAUTH_RATE_LIMIT)
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db)
):

    try:
        user_id = consume_oauth_state(db, state, "github")
    except InvalidOAuthState as e:
        return _frontend_redirect(github="error", reason=e.code)

    if error or not code:
        return _frontend_redirect(github="error", reason="access_denied")

    try:

        token_data = exchange_code_for_token(code)

        if "access_token" not in token_data:
            return _frontend_redirect(github="error", reason="token_exchange_failed")

        # Store the GitHub login so the UI can show which account is connected.
        try:
            login = GitHubClient(token_data["access_token"]).user().get("login")
        except Exception:
            logger.warning("Could not read the GitHub login after connecting")
            login = None

        save_github_credentials(
            db,
            user_id,
            token_data,
            account_name=login
        )

    except Exception:

        # Details go to the server log only; nothing is reflected to the browser.
        logger.exception("GitHub OAuth callback failed")

        return _frontend_redirect(github="error", reason="token_exchange_failed")

    return _frontend_redirect(github="connected")


@router.get("/status", response_model=rm.GithubStatus)
def github_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    connection = get_platform_connection(db, current_user["id"], "github")
    connected = connection is not None and bool(connection.connected)

    return {
        "connected": connected,
        "account_name": connection.account_name if connected else None
    }


@router.post("/disconnect", response_model=rm.DisconnectResponse)
def disconnect(
    current_user=Depends(get_current_user),
    purge: bool = False,
    db: Session = Depends(get_db)
):

    connection = get_platform_connection(db, current_user["id"], "github")
    revoked = None

    # Revoke the grant at GitHub first; disconnect locally even if that fails.
    if connection is not None and connection.access_token:
        revoked = revoke_grant(connection.access_token)
        if not revoked:
            logger.warning("GitHub revoke failed for user %s; disconnecting locally anyway", current_user["id"])

    disconnect_github(
        db,
        current_user["id"]
    )

    # ?purge=true also removes every indexed file of this platform (this user only).
    purged = purge_platform(current_user["id"], "github") if purge else 0

    return {
        "status": "success",
        "revoked": revoked,
        "purged_files": purged,
        "connected": False,
        "message": "GitHub disconnected successfully."
    }
