import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.core.errors import AppError
from app.database.db import get_db
from app.models.platforms import PlatformName
from app.scheduler.jobs import (
    ActiveJobExists,
    enqueue_jobs,
    get_user_job,
    indexed_platforms,
    job_errors,
    latest_jobs_per_platform,
    prioritize_job,
    JobNotQueued,
    recent_jobs,
    request_cancel,
    serialize_job
)
from app.scheduler.worker import notify_worker
from app.models import response_models as rm


router = APIRouter(
    prefix="/index",
    tags=["Index"]
)


class IndexRequest(BaseModel):

    priority_platform: PlatformName

    platforms: list[PlatformName] = Field(min_length=1)


@router.get("/health")
def health():

    return {
        "status": "Index API Ready"
    }


@router.post("/", response_model=rm.IndexQueuedResponse)
def index(
    request: IndexRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Queue one new job per platform (priority platform first)."""

    priority_platform = request.priority_platform.value
    platforms = list(dict.fromkeys(p.value for p in request.platforms))

    try:
        jobs = enqueue_jobs(db, current_user["id"], priority_platform, platforms)
    except ActiveJobExists as conflict:
        raise AppError(
            409,
            "Indexing is already queued or running for: " + ", ".join(conflict.platforms) + ".",
            code="job_already_active"
        )

    notify_worker()

    return {
        "status": "success",
        "message": "Indexing queued",
        "priority_platform": priority_platform,
        "platforms": [job.platform for job in jobs],
        "jobs": [serialize_job(job) for job in jobs]
    }


@router.get("/jobs", response_model=list[rm.JobWithHistory], response_model_exclude_unset=True)
def get_jobs(
    history: int = Query(0, ge=0, le=20, description="Also return the last N jobs per platform."),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Latest job per platform for the current user.

    `indexed` is true when the platform has ever finished a run successfully
    (completed or completed_with_errors), even while a new job is queued or
    running, so the UI never hides a platform's results during a re-index.
    """

    indexed = set(indexed_platforms(db, current_user["id"]))

    jobs = [
        {**serialize_job(job), "indexed": job.platform in indexed}
        for job in latest_jobs_per_platform(db, current_user["id"])
    ]

    if history:
        for job in jobs:
            job["history"] = [
                serialize_job(old) for old in recent_jobs(db, current_user["id"], job["platform"], history)
            ]

    return jobs


def _owned_job(db: Session, user_id, job_id: uuid.UUID):

    job = get_user_job(db, user_id, job_id)

    if job is None:
        # Same answer for "missing" and "someone else's".
        raise AppError(404, "Job not found.")

    return job


@router.get("/jobs/{job_id}/errors", response_model=rm.JobErrorsResponse)
def get_job_errors(
    job_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    job = _owned_job(db, current_user["id"], job_id)

    return {
        "job_id": str(job.id),
        "failed_files": job.failed_files,
        "errors": [
            {
                "file": error.file_ref,
                "error": error.error,
                "created_at": error.created_at
            }
            for error in job_errors(db, job.id)
        ]
    }


@router.post("/jobs/{job_id}/prioritize", response_model=rm.Job)
def prioritize(
    job_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """"Index next": run this queued job before the user's other queued jobs."""

    try:
        job = prioritize_job(db, _owned_job(db, current_user["id"], job_id))
    except JobNotQueued:
        raise AppError(409, "Only a queued job can be moved to the front.", code="job_not_queued")

    return serialize_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=rm.Job)
def cancel_job(
    job_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    job = request_cancel(db, _owned_job(db, current_user["id"], job_id))

    return serialize_job(job)
