from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.db import get_db

from app.auth.auth_dependency import get_current_user

from app.database.platform_connection_service import (
    is_platform_connected
)

from app.platforms.google_drive.auth import authenticate

from app.platforms.google_drive.google_drive_credentials import (
    save_google_credentials,
    disconnect_google_credentials
)

router = APIRouter(
    prefix="/platforms/google-drive",
    tags=["Google Drive"]
)


@router.get("/connect")
def connect_google_drive(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    if is_platform_connected(

        db,

        current_user["id"],

        "google_drive"

    ):

        return {

            "status": "success",

            "connected": True,

            "message": "Google Drive already connected."

        }

    try:

        creds = authenticate()

        save_google_credentials(

            db=db,

            user_id=current_user["id"],

            creds=creds,

            account_email=None,

            account_name=None

        )

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
def google_drive_status(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    return {

        "connected": is_platform_connected(

            db,

            current_user["id"],

            "google_drive"

        )

    }


@router.post("/disconnect")
def disconnect_google_drive(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    disconnect_google_credentials(

        db,

        current_user["id"]

    )

    return {

        "status": "success",

        "connected": False,

        "message": "Google Drive disconnected successfully."

    }