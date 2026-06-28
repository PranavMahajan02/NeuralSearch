from fastapi import APIRouter

from app.services.delete_service import delete_file

router = APIRouter()


@router.delete("/")
def delete(filename: str):

    result = delete_file(filename)

    return result


@router.get("/health")
def health():

    return {
        "status": "Delete API Ready"
    }