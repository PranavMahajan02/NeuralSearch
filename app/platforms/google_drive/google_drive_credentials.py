import json

from google.oauth2.credentials import Credentials

from app.database.platform_connection_service import (
    save_platform_connection,
    get_platform_connection,
    disconnect_platform
)


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]


def save_google_credentials(

    db,

    user_id,

    creds,

    account_email=None,

    account_name=None

):

    save_platform_connection(

        db=db,

        user_id=user_id,

        platform="google_drive",

        account_email=account_email,

        account_name=account_name,

        access_token=creds.token,

        refresh_token=creds.refresh_token

    )

    connection = get_platform_connection(

        db,

        user_id,

        "google_drive"

    )

    connection.token_json = creds.to_json()

    db.commit()


def load_google_credentials(

    db,

    user_id

):

    connection = get_platform_connection(

        db,

        user_id,

        "google_drive"

    )

    if connection is None:

        return None

    if not connection.connected:

        return None

    if not connection.token_json:

        return None

    token_data = json.loads(

        connection.token_json

    )

    return Credentials.from_authorized_user_info(

        token_data,

        SCOPES

    )


def disconnect_google_credentials(

    db,

    user_id

):

    disconnect_platform(

        db,

        user_id,

        "google_drive"

    )