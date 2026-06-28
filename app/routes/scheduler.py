from fastapi import APIRouter
from app.models.scheduler import SchedulerRequest
from app.scheduler.status import get_status
from app.scheduler.worker import start_worker
from app.scheduler.queue import create_queue

router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"]
)


@router.get("/status")
def scheduler_status():

    return get_status()

@router.post("/start")
def start_scheduler(request: SchedulerRequest):

    create_queue(
        request.priority_platform,
        request.platforms
    )

    start_worker()

    return {
        "message": "Scheduler started."
    }