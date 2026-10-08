from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.db import get_db

from app.auth.auth_dependency import get_current_user

from app.core.config import settings
from app.models import response_models as rm
from app.models.request_models import FolderRequest
from app.core.local_folders import normalize_folder, validate_local_folder
from app.platforms.local.local_platform import sync_deleted_sources as purge_unregistered_local_sources

from app.database.local_storage_service import (
    get_local_folders,
    add_local_folder,
    remove_local_folder
)


def picker_available() -> bool:
    """The tkinter folder picker is mounted only in development (app/main.py)."""

    return settings.ENV == "development"


router = APIRouter(
    prefix="/platforms/local",
    tags=["Local Platform"]
)


@router.get("/folders", response_model=rm.FoldersResponse, response_model_exclude_unset=True)
def get_folders(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "picker_available": picker_available(),

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }


@router.post("/folders", response_model=rm.FoldersResponse, response_model_exclude_unset=True)
def add_folder(

    request: FolderRequest,

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    add_local_folder(

        db,

        current_user["id"],

        validate_local_folder(request.folder)

    )

    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "status": "success",

        "picker_available": picker_available(),

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }


@router.delete("/folders", response_model=rm.FoldersResponse, response_model_exclude_unset=True)
def delete_folder(

    request: FolderRequest,

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    # Accept the stored form or any spelling that normalizes to it.
    for candidate in {request.folder, normalize_folder(request.folder)}:

        remove_local_folder(
            db,
            current_user["id"],
            candidate
        )

    # Purge the removed folder's files from the index (this user only),
    # except files still covered by another of the user's folders.
    purged = purge_unregistered_local_sources(
        current_user["id"],
        [folder.folder_path for folder in get_local_folders(db, current_user["id"])]
    )


    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "status": "success",
        "purged_files": purged,

        "picker_available": picker_available(),

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }