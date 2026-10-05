from app.database.platform_connection_service import (
    disconnect_platform,
    get_platform_connection,
    save_platform_connection,
)


def save_google_credentials(db, user_id, creds, account_email=None, account_name=None):
    """Store the OAuth credentials (token columns are encrypted at rest)."""

    save_platform_connection(
        db=db,
        user_id=user_id,
        platform="google_drive",
        account_email=account_email,
        account_name=account_name,
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        token_json=creds.to_json(),
        token_type="Bearer",
    )


def get_google_access_token(db, user_id):

    connection = get_platform_connection(db, user_id, "google_drive")

    return connection.access_token if connection is not None else None


def disconnect_google_credentials(db, user_id):

    disconnect_platform(db, user_id, "google_drive")
