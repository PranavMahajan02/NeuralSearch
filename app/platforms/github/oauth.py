"""GitHub OAuth app: authorization URL, code exchange, token access, revoke."""

import json
import logging
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.platform_connection_service import get_platform_connection
from app.platforms import http
from app.platforms.errors import PlatformPreconditionError
from app.platforms.oauth_state import (  # noqa: F401  (re-exported)
    OAUTH_STATE_TTL,
    InvalidOAuthState,
)
from app.platforms.oauth_state import (
    consume_oauth_state as _consume_state,
)
from app.platforms.oauth_state import (
    create_oauth_state as _create_state,
)

logger = logging.getLogger("cogniseek.github")

GITHUB_CONFIG = settings.GITHUB_OAUTH_CONFIG_PATH

REDIRECT_URI = f"{settings.BACKEND_PUBLIC_URL}/platforms/github/callback"


def load_config():

    with open(GITHUB_CONFIG) as f:
        return json.load(f)


def get_authorization_url(state):

    config = load_config()

    return "https://github.com/login/oauth/authorize?" + urlencode({
        "client_id": config["client_id"],
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": "repo read:user"
    })


def exchange_code_for_token(code):

    config = load_config()

    response = http.request(
        "POST",
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    response.raise_for_status()

    return response.json()


def get_access_token(db: Session, user_id):

    connection = get_platform_connection(db, user_id, "github")

    if connection is None or not connection.connected or not connection.access_token:
        raise PlatformPreconditionError("GitHub is not connected.")

    return connection.access_token


def is_connected(db: Session, user_id):

    connection = get_platform_connection(db, user_id, "github")

    return connection is not None and connection.connected


def revoke_grant(access_token: str) -> bool:
    """Revoke the whole OAuth grant on GitHub (DELETE /applications/{id}/grant,
    basic auth with the app's client id/secret). Returns False on failure."""

    try:
        config = load_config()
        response = http.request(
            "DELETE",
            f"https://api.github.com/applications/{config['client_id']}/grant",
            auth=(config["client_id"], config["client_secret"]),
            headers={"Accept": "application/vnd.github+json"},
            json={"access_token": access_token},
            max_tries=2
        )
    except Exception as error:
        logger.warning("GitHub grant revoke failed: %s", type(error).__name__)
        return False

    if response.status_code not in (204, 404):
        logger.warning("GitHub grant revoke returned HTTP %s", response.status_code)
        return False

    return True


# Kept with GitHub's defaults for existing callers.

def create_oauth_state(db: Session, user_id, platform: str = "github") -> str:

    return _create_state(db, user_id, platform)


def consume_oauth_state(db: Session, state: str, platform: str = "github"):

    return _consume_state(db, state, platform)
