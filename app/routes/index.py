from fastapi import APIRouter
from pydantic import BaseModel

from app.scheduler.queue import create_queue
from app.scheduler.worker import start_worker

router = APIRouter(
    prefix="/index",
    tags=["Index"]
)


class IndexRequest(BaseModel):

    priority_platform: str
    platforms: list[str]


@router.get("/health")
def health():

    return {
        "status": "Index API Ready"
    }


@router.post("/")
def index(request: IndexRequest):

    create_queue(
        request.priority_platform,
        request.platforms
    )

    start_worker()

    return {
        "status": "success",
        "message": "Indexing started",
        "priority_platform": request.priority_platform,
        "platforms": request.platforms
    }