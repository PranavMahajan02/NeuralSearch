from fastapi import APIRouter

from app.models.request_models import FolderRequest
from app.platforms.registry import platform_manager

from app.config.local_config import (
    load_local_folders,
    add_folder,
    remove_folder
)

router = APIRouter(
    prefix="/platforms/local",
    tags=["Local Platform"]
)


@router.get("/folders")
def get_folders():

    return {
        "folders": load_local_folders()
    }


@router.post("/folders")
def add_local_folder(request: FolderRequest):

    add_folder(request.folder)

    return {
        "status": "success",
        "message": "Folder added successfully.",
        "folders": load_local_folders()
    }

@router.delete("/folders")
def delete_local_folder(request: FolderRequest):

    remove_folder(request.folder)

    return {
        "status": "success",
        "message": "Folder removed successfully.",
        "folders": load_local_folders()
    }

@router.post("/index")
def index_local_storage():

    local = platform_manager.get("local")

    if local is None:
        return {
            "status": "error",
            "message": "Local platform not registered."
        }

    from threading import Thread

    Thread(
        target=local.index,
        daemon=True
    ).start()    

    return {
        "status": "success",
        "message": "Local indexing completed."
    }