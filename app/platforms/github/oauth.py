import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

from sqlalchemy.orm import Session

from app.database.models import OAuthState
from app.platforms.errors import PlatformPreconditionError
from app.database.platform_connection_service import (
    get_platform_connection
)

from app.core.config import settings

GITHUB_CONFIG = settings.GITHUB_OAUTH_CONFIG_PATH

REDIRECT_URI = f"{settings.BACKEND_PUBLIC_URL}/platforms/github/callback"


def load_config():

    with open(GITHUB_CONFIG, "r") as f:

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

    response = requests.post(

        "https://github.com/login/oauth/access_token",
        timeout=15,

        headers={

            "Accept": "application/json"

        },

        data={

            "client_id": config["client_id"],

            "client_secret": config["client_secret"],

            "code": code,

            "redirect_uri": REDIRECT_URI

        }

    )

    response.raise_for_status()

    return response.json()


def get_access_token(

    db: Session,

    user_id

):

    connection = get_platform_connection(

        db,

        user_id,

        "github"

    )

    if connection is None or not connection.connected or not connection.access_token:

        raise PlatformPreconditionError(

            "GitHub is not connected."

        )

    return connection.access_token


def is_connected(

    db: Session,

    user_id

):

    connection = get_platform_connection(

        db,

        user_id,

        "github"

    )

    return (

        connection is not None

        and

        connection.connected

    )


# ==========================================================
# OAUTH STATE (CSRF protection, single use, 10 minute TTL)
# ==========================================================

OAUTH_STATE_TTL = timedelta(minutes=10)


class InvalidOAuthState(Exception):

    def __init__(self, code: str):

        super().__init__(code)
        self.code = code


def create_oauth_state(db: Session, user_id, platform: str = "github") -> str:

    state = secrets.token_urlsafe(32)

    db.add(
        OAuthState(
            state=state,
            user_id=user_id,
            platform=platform,
            expires_at=datetime.utcnow() + OAUTH_STATE_TTL,
            used=False
        )
    )

    db.commit()

    return state


def consume_oauth_state(db: Session, state: str, platform: str = "github"):
    """Validate a callback state and return the user_id stored with it.

    The user is taken from the DB row, never from the state string itself.
    """

    if not state:
        raise InvalidOAuthState("missing_state")

    row = (
        db.query(OAuthState)
        .filter(
            OAuthState.state == state,
            OAuthState.platform == platform
        )
        .with_for_update()
        .first()
    )

    if row is None:
        raise InvalidOAuthState("invalid_state")

    if row.used:
        raise InvalidOAuthState("state_already_used")

    if row.expires_at < datetime.utcnow():
        raise InvalidOAuthState("state_expired")

    row.used = True
    db.commit()

    return row.user_id
