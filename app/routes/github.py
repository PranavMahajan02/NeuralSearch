import webbrowser
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import HTMLResponse

from sqlalchemy.orm import Session

from app.database.db import get_db

from app.auth.auth_dependency import get_current_user

from app.platforms.github.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    is_connected
)

from app.platforms.github.github_credentials import (
    save_github_credentials,
    disconnect_github
)

from app.platforms.github.github_service import (
    get_user
)

router = APIRouter(
    prefix="/platforms/github",
    tags=["GitHub"]
)


@router.get("/connect")
def connect_github(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    if is_connected(

        db,

        current_user["id"]

    ):

        user = get_user(

            db,

            current_user["id"]

        )

        return {

            "status": "success",

            "connected": True,

            "username": user["login"],

            "message": "GitHub already connected."

        }

    state = str(

        current_user["id"]

    )

    url = get_authorization_url(

        state

    )

    webbrowser.open(

        url

    )

    return {

        "status": "success",

        "connected": False,

        "message": "GitHub authorization started."

    }


@router.get(
    "/callback",
    response_class=HTMLResponse
)
def github_callback(

    code: str,

    state: str,

    db: Session = Depends(get_db)

):

    try:

        token_data = exchange_code_for_token(

            code

        )

        try:

            user_id = UUID(

                state

            )

        except ValueError:

            return """
            <html>
                <body style="font-family:Arial;text-align:center;margin-top:100px;">
                    <h2>❌ Invalid OAuth State</h2>
                    <p>The authentication request is invalid.</p>
                </body>
            </html>
            """

        save_github_credentials(

            db,

            user_id,

            token_data

        )

        return """
        <html>
            <body style="font-family:Arial;text-align:center;margin-top:100px;">
                <h2>✅ GitHub Connected Successfully</h2>
                <p>You can now close this window and return to OmniSearch+.</p>
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
def github_status(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    return {

        "connected": is_connected(

            db,

            current_user["id"]

        )

    }


@router.post("/disconnect")
def disconnect(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    disconnect_github(

        db,

        current_user["id"]

    )

    return {

        "status": "success",

        "connected": False,

        "message": "GitHub disconnected successfully."

    }