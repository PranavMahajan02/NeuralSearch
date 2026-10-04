import json
import requests

from sqlalchemy.orm import Session

from app.database.platform_connection_service import (
    get_platform_connection
)

GITHUB_CONFIG = "credentials/github_oauth.json"

REDIRECT_URI = "http://127.0.0.1:8000/platforms/github/callback"


def load_config():

    with open(GITHUB_CONFIG, "r") as f:

        return json.load(f)


import secrets

def get_authorization_url(state):

    config = load_config()

    return (

        "https://github.com/login/oauth/authorize"

        f"?client_id={config['client_id']}"

        f"&redirect_uri={REDIRECT_URI}"

        f"&state={state}"

        "&scope=repo read:user"

    )


def exchange_code_for_token(code):

    config = load_config()

    response = requests.post(

        "https://github.com/login/oauth/access_token",

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

    if connection is None:

        raise Exception(

            "GitHub not connected."

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