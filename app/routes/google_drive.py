import os
from fastapi import APIRouter

from app.platforms.google_drive.auth import authenticate

TOKEN_FILE = "credentials/token.json"
router = APIRouter(
    prefix="/platforms/google-drive",
    tags=["Google Drive"]
)


@router.get("/connect")
def connect_google_drive():

    if os.path.exists(TOKEN_FILE):

        return {
            "status": "success",
            "connected": True,
            "message": "Google Drive already connected."
        }

    try:

        authenticate()

        return {
            "status": "success",
            "connected": True,
            "message": "Google Drive connected successfully."
        }

    except Exception as e:

        return {
            "status": "error",
            "connected": False,
            "message": str(e)
        }

@router.get("/status")
def google_drive_status():

    return {
        "connected": os.path.exists(TOKEN_FILE)
    }

@router.post("/disconnect")
def disconnect_google_drive():

    try:

        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)

        return {
            "status": "success",
            "connected": False,
            "message": "Google Drive disconnected successfully."
        }

    except Exception as e:

        return {
            "status": "error",
            "connected": True,
            "message": str(e)
        }