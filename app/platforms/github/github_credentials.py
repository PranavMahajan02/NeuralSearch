import json

from app.database.platform_connection_service import (
    save_platform_connection,
    get_platform_connection,
    disconnect_platform
)


def save_github_credentials(

    db,

    user_id,

    token_data

):

    save_platform_connection(

        db=db,

        user_id=user_id,

        platform="github",

        access_token=token_data["access_token"],

        refresh_token=None,

        token_json=json.dumps(token_data),

        token_type=token_data.get("token_type"),

        account_email=None,

        account_name=None

    )


def load_github_access_token(

    db,

    user_id

):

    connection = get_platform_connection(

        db,

        user_id,

        "github"

    )

    if connection is None:

        return None

    return connection.access_token


def disconnect_github(

    db,

    user_id

):

    disconnect_platform(

        db,

        user_id,

        "github"

    )