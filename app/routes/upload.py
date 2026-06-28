from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import BackgroundTasks

from app.services.upload_service import save_uploaded_file
from app.services.upload_service import process_uploaded_file

router = APIRouter()


@router.post("/")
def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    result = save_uploaded_file(file)

    if result["status"] == "duplicate":

        return {
            "status": "duplicate",
            "filename": file.filename,
            "message": "File already exists.",
            "path": result["path"]
        }

    background_tasks.add_task(
    process_uploaded_file,
    result["path"]
    )

    return {
        "status": "uploaded",
        "filename": file.filename,
        "message": "Uploaded Successfully",
        "path": result["path"]
    }


@router.get("/health")
def health():

    return {
        "status": "Upload API Ready"
    }