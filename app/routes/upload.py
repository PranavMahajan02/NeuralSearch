from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.services.upload_service import index_upload_in_background, save_uploaded_file

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)


# Multipart framing overhead allowed on top of MAX_UPLOAD_MB.
MULTIPART_OVERHEAD = 64 * 1024


@router.post("/")
def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):

    declared = request.headers.get("content-length")

    if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes + MULTIPART_OVERHEAD:
        raise AppError(413, f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.")

    result = save_uploaded_file(file, current_user["id"])

    background_tasks.add_task(
        index_upload_in_background,
        current_user["id"],
        result["path"]
    )

    return {
        "status": "uploaded",
        "filename": result["filename"],
        "message": "Uploaded Successfully"
    }


@router.get("/health")
def health():

    return {
        "status": "Upload API Ready"
    }
