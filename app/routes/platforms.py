from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.db import get_db

from app.auth.auth_dependency import get_current_user

from app.models.request_models import FolderRequest

from app.database.local_storage_service import (
    get_local_folders,
    add_local_folder,
    remove_local_folder
)

router = APIRouter(
    prefix="/platforms/local",
    tags=["Local Platform"]
)


@router.get("/folders")
def get_folders(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }


@router.post("/folders")
def add_folder(

    request: FolderRequest,

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    add_local_folder(

        db,

        current_user["id"],

        request.folder

    )

    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "status": "success",

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }


@router.delete("/folders")
def delete_folder(

    request: FolderRequest,

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    remove_local_folder(

        db,

        current_user["id"],

        request.folder

    )

    folders = get_local_folders(

        db,

        current_user["id"]

    )

    return {

        "status": "success",

        "folders": [

            folder.folder_path

            for folder in folders

        ]

    }