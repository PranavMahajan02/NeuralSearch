import os
import webbrowser

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.platforms.github.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    is_connected
)

from app.platforms.github.github_service import get_user

TOKEN_FILE = "credentials/github_oauth_token.json"

router = APIRouter(
    prefix="/platforms/github",
    tags=["GitHub"]
)


@router.get("/connect")
def connect_github():

    try:

        if is_connected():

            user = get_user()

            return {
                "status": "success",
                "connected": True,
                "username": user["login"],
                "message": "GitHub already connected."
            }

        url = get_authorization_url()

        webbrowser.open(url)

        return {
            "status": "success",
            "connected": False,
            "message": "GitHub authorization started."
        }

    except Exception as e:

        return {
            "status": "error",
            "connected": False,
            "message": str(e)
        }


@router.get(
    "/callback",
    response_class=HTMLResponse
)
def github_callback(code: str):

    try:

        exchange_code_for_token(code)

        return """
        <html>
            <body style="font-family:Arial;text-align:center;margin-top:100px;">
                <h2>✅ GitHub Connected Successfully</h2>
                <p>You can now close this window and return to CogniSeek.</p>
            </body>
        </html>
        """

    except Exception as e:

        return f"""
        <html>
            <body style="font-family:Arial;text-align:center;margin-top:100px;">
                <h2>❌ GitHub Connection Failed</h2>
                <p>{str(e)}</p>
            </body>
        </html>
        """


@router.get("/status")
def github_status():

    try:

        if not is_connected():

            return {
                "connected": False
            }

        get_user()

        return {
            "connected": True
        }

    except Exception:

        return {
            "connected": False
        }


@router.post("/disconnect")
def disconnect_github():

    try:

        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)

        return {
            "status": "success",
            "connected": False,
            "message": "GitHub disconnected successfully."
        }

    except Exception as e:

        return {
            "status": "error",
            "connected": True,
            "message": str(e)
        }