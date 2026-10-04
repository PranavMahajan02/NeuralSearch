from fastapi import APIRouter
from fastapi import Depends

from app.auth.auth_dependency import get_current_user
from app.services.delete_service import delete_file


router = APIRouter()


@router.get("/health")
def health():

    return {
        "status": "Delete API Ready"
    }


@router.delete("/{filename}")
def delete(
    filename: str,
    current_user=Depends(get_current_user)
):

    return delete_file(
        current_user["id"],
        filename
    )
