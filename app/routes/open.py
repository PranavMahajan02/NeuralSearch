from fastapi import APIRouter

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
def open_file(request: OpenRequest):

    return open_result(request)