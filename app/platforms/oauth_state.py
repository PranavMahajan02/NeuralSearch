"""Single-use OAuth `state` values (CSRF protection), shared by all connectors.

A random state is stored with the user who started the flow, the platform,
an expiry (10 minutes) and - for PKCE - the code_verifier. The callback
looks the row up, checks it, marks it used, and takes the user from the row:
never from anything the browser sent.
"""

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.database.models import OAuthState

OAUTH_STATE_TTL = timedelta(minutes=10)


class InvalidOAuthState(Exception):

    def __init__(self, code: str):

        super().__init__(code)
        self.code = code


def create_oauth_state(db: Session, user_id, platform: str, code_verifier: str | None = None) -> str:

    state = secrets.token_urlsafe(32)

    db.add(
        OAuthState(
            state=state,
            user_id=user_id,
            platform=platform,
            expires_at=utcnow() + OAUTH_STATE_TTL,
            used=False,
            code_verifier=code_verifier
        )
    )

    db.commit()

    return state


def consume_oauth_state_row(db: Session, state: str, platform: str) -> tuple[object, str | None]:
    """(user_id, code_verifier) for a valid state; raises InvalidOAuthState."""

    if not state:
        raise InvalidOAuthState("missing_state")

    row = (
        db.query(OAuthState)
        .filter(OAuthState.state == state, OAuthState.platform == platform)
        .with_for_update()
        .first()
    )

    if row is None:
        raise InvalidOAuthState("invalid_state")

    if row.used:
        raise InvalidOAuthState("state_already_used")

    if row.expires_at < utcnow():
        raise InvalidOAuthState("state_expired")

    row.used = True
    db.commit()

    return row.user_id, row.code_verifier


def consume_oauth_state(db: Session, state: str, platform: str):

    return consume_oauth_state_row(db, state, platform)[0]
