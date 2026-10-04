from fastapi import APIRouter
from fastapi import Depends

from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.scheduler.queue import create_queue
from app.scheduler.worker import start_worker

from app.database.db import get_db
from app.database.models import IndexingJob

from app.auth.auth_dependency import get_current_user

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
def index(

    request: IndexRequest,

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    # ---------------------------------------
    # Create indexing jobs for this user
    # ---------------------------------------

    for platform in request.platforms:

        job = (

            db.query(IndexingJob)

            .filter(

                IndexingJob.user_id == current_user["id"],

                IndexingJob.platform == platform

            )

            .order_by(IndexingJob.started_at.desc())

            .first()

        )

        from datetime import datetime

        if job:

            if platform == request.priority_platform:

                job.status = "indexing"

            else:

                job.status = "queued"

            job.started_at = datetime.utcnow()
            job.completed_at = None
            job.indexed_files = 0
            job.total_files = 0
            job.current_file = ""

        else:

            job = IndexingJob(
                user_id=current_user["id"],
                platform=platform,
                status=(
                    "indexing"
                    if platform == request.priority_platform
                    else "queued"
                ),
                started_at=datetime.utcnow(),
                indexed_files=0,
                total_files=0,
                current_file=""
            )

            db.add(job)

    db.commit()

    # ---------------------------------------
    # Start scheduler
    # ---------------------------------------

    create_queue(

        current_user["id"],

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