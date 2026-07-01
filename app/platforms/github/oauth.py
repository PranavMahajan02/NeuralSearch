import json
import os
import requests

GITHUB_CONFIG = "credentials/github_oauth.json"
TOKEN_FILE = "credentials/github_oauth_token.json"

REDIRECT_URI = "http://127.0.0.1:8000/platforms/github/callback"


def load_config():

    with open(GITHUB_CONFIG, "r") as f:
        return json.load(f)


def get_authorization_url():

    config = load_config()

    return (
        "https://github.com/login/oauth/authorize"
        f"?client_id={config['client_id']}"
        f"&redirect_uri={REDIRECT_URI}"
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

    token_data = response.json()

    with open(TOKEN_FILE, "w") as f:

        json.dump(
            token_data,
            f,
            indent=4
        )

    return token_data

def get_access_token():

    if not os.path.exists(TOKEN_FILE):

        raise Exception("GitHub OAuth token not found.")

    with open(TOKEN_FILE, "r") as f:

        token_data = json.load(f)

    return token_data["access_token"]


def is_connected():

    return os.path.exists(TOKEN_FILE)