import logging

from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.db import get_db
from app.services.index_store import purge_platform

from app.auth.auth_dependency import get_current_user

from app.database.platform_connection_service import (
    is_platform_connected
)

from app.platforms.google_drive.auth import authenticate

from app.platforms.google_drive.google_drive_credentials import (
    save_google_credentials,
    disconnect_google_credentials
)

logger = logging.getLogger("cogniseek.google_drive")


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

    except Exception:

        # Details stay in the server log; the client gets a generic error.
        logger.exception("Google Drive connect failed")

        raise AppError(502, "Google Drive connection failed.")


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

    purge: bool = False,

    db: Session = Depends(get_db)

):

    disconnect_google_credentials(

        db,

        current_user["id"]

    )

    # ?purge=true also removes every indexed file of this platform (this user only).
    purged = purge_platform(current_user["id"], "google_drive") if purge else 0

    return {

        "status": "success",

        "purged_files": purged,
        "connected": False,

        "message": "Google Drive disconnected successfully."

    }