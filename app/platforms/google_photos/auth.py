from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import os

SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.readonly"
]

TOKEN_FILE = "credentials/google_photos_token.json"
CLIENT_SECRET = "credentials/client_secret.json"


def get_credentials():

    creds = None

    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET,
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        with open(TOKEN_FILE, "w") as token:

            token.write(
                creds.to_json()
            )

    return creds