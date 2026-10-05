import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.db import get_db
from app.services.index_store import purge_platform
from app.auth.auth_dependency import get_current_user

from app.platforms.github.oauth import (
    InvalidOAuthState,
    consume_oauth_state,
    create_oauth_state,
    exchange_code_for_token,
    get_authorization_url,
    is_connected
)

from app.platforms.github.github_credentials import (
    save_github_credentials,
    disconnect_github
)

from app.platforms.github.github_service import (
    get_user
)


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


@router.get("/connect")
def connect_github(
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
def github_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
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

        save_github_credentials(
            db,
            user_id,
            token_data
        )

    except Exception:

        # Details go to the server log only; nothing is reflected to the browser.
        logger.exception("GitHub OAuth callback failed")

        return _frontend_redirect(github="error", reason="token_exchange_failed")

    return _frontend_redirect(github="connected")


@router.get("/status")
def github_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return {
        "connected": is_connected(
            db,
            current_user["id"]
        )
    }


@router.post("/disconnect")
def disconnect(
    current_user=Depends(get_current_user),
    purge: bool = False,
    db: Session = Depends(get_db)
):

    disconnect_github(
        db,
        current_user["id"]
    )

    # ?purge=true also removes every indexed file of this platform (this user only).
    purged = purge_platform(current_user["id"], "github") if purge else 0

    return {
        "status": "success",
        "purged_files": purged,
        "connected": False,
        "message": "GitHub disconnected successfully."
    }
