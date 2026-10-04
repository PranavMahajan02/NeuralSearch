from fastapi import APIRouter
from fastapi import Depends

from app.models.scheduler import SchedulerRequest
from app.scheduler.status import get_status_for_user
from app.scheduler.worker import start_worker
from app.scheduler.queue import create_queue
from app.auth.auth_dependency import get_current_user


router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"]
)


@router.get("/status")
def scheduler_status(
    current_user=Depends(get_current_user)
):

    return get_status_for_user(
        current_user["id"]
    )


@router.post("/start")
def start_scheduler(
    request: SchedulerRequest,
    current_user=Depends(get_current_user)
):

    create_queue(
        current_user["id"],
        request.priority_platform.value,
        list(dict.fromkeys(p.value for p in request.platforms))
    )

    start_worker()

    return {
        "message": "Scheduler started."
    }
