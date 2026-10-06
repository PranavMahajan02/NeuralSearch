"""Google Drive web OAuth (replaces InstalledAppFlow.run_local_server).

The browser goes to Google's consent page and comes back to
GET /platforms/google-drive/callback. State is single-use and bound to the
user in the DB; PKCE's code_verifier is kept server-side with that state.
"""

import os
import secrets

from app.core.config import settings
from app.platforms import http
from app.platforms.google_drive.drive_service import SCOPES


# Google may grant a superset of the requested scopes (include_granted_scopes);
# oauthlib would otherwise treat that as an error.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


def new_code_verifier() -> str:
    """PKCE verifier: 86 chars of [A-Za-z0-9_-] (RFC 7636 allows 43-128)."""

    return secrets.token_urlsafe(64)


def build_flow(code_verifier=None):
    """The verifier is always set when the Flow is built.

    google_auth_oauthlib only autogenerates one inside authorization_url(),
    so reading flow.code_verifier before that returned None and the callback
    then exchanged the code without a verifier ("Missing code verifier").
    """

    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_PATH,
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
        code_verifier=code_verifier or new_code_verifier(),
        autogenerate_code_verifier=False,
    )


def authorization_url(state: str, flow) -> str:

    url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=state,
    )

    return url


def exchange_code(code: str, code_verifier: str):
    """Code -> google.oauth2.credentials.Credentials (PKCE verified by Google)."""

    flow = build_flow(code_verifier=code_verifier)
    flow.fetch_token(code=code)

    return flow.credentials


def account_email(credentials) -> str:

    response = http.request(
        "GET",
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    )

    if response.status_code != 200:
        return None

    return response.json().get("email")
