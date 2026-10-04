from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.database.db import get_db
from app.models.request_models import OpenRequest
from app.services.open_service import open_result


router = APIRouter(
    prefix="/open",
    tags=["Open"]
)


@router.get("/health")
def health():

    return {
        "status": "Open API Ready"
    }


@router.post("/")
def open_file(
    request: OpenRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return open_result(
        db,
        current_user["id"],
        request
    )
