from sqlalchemy.orm import Session

from app.database.models import PlatformConnection


def get_platform_connection(
    db: Session,
    user_id,
    platform: str
):

    return (

        db.query(PlatformConnection)

        .filter(

            PlatformConnection.user_id == user_id,

            PlatformConnection.platform == platform

        )

        .first()

    )


def is_platform_connected(
    db: Session,
    user_id,
    platform: str
):

    connection = get_platform_connection(

        db,

        user_id,

        platform

    )

    return (

        connection is not None

        and

        connection.connected

    )


def save_platform_connection(

    db: Session,

    user_id,

    platform: str,

    account_email: str = None,

    account_name: str = None,

    access_token: str = None,

    refresh_token: str = None,

    token_json: str = None,

    token_type: str = None

):

    connection = get_platform_connection(

        db,

        user_id,

        platform

    )

    if connection:

        connection.account_email = account_email

        connection.account_name = account_name

        connection.access_token = access_token

        connection.refresh_token = refresh_token

        connection.token_json = token_json

        connection.token_type = token_type

        connection.connected = True

    else:

        connection = PlatformConnection(

            user_id=user_id,

            platform=platform,

            account_email=account_email,

            account_name=account_name,

            access_token=access_token,

            refresh_token=refresh_token,

            token_json=token_json,

            token_type=token_type,

            connected=True

        )

        db.add(connection)

    db.commit()

    db.refresh(connection)

    return connection


def update_platform_tokens(

    db: Session,

    user_id,

    platform: str,

    access_token: str,

    refresh_token: str = None

):

    connection = get_platform_connection(

        db,

        user_id,

        platform

    )

    if connection is None:

        return None

    connection.access_token = access_token

    if refresh_token:

        connection.refresh_token = refresh_token

    db.commit()

    db.refresh(connection)

    return connection


def disconnect_platform(

    db: Session,

    user_id,

    platform: str

):

    connection = get_platform_connection(

        db,

        user_id,

        platform

    )

    if connection is None:

        return False

    connection.connected = False

    connection.access_token = None

    connection.refresh_token = None
    connection.token_json = None
    connection.token_type = None

    db.commit()

    return True