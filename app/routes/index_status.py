from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import IndexingJob
from app.auth.auth_dependency import get_current_user

router = APIRouter(
    prefix="/index",
    tags=["Index"]
)


@router.get("/jobs")
def get_jobs(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    latest_jobs = []

    platforms = ["local", "google_drive", "github"]

    for platform in platforms:

        job = (

            db.query(IndexingJob)

            .filter(
                IndexingJob.user_id == current_user["id"],
                IndexingJob.platform == platform
            )

            .order_by(IndexingJob.started_at.desc())

            .first()

        )

        if job:

            latest_jobs.append(job)

    return [

        {

            "platform": job.platform,

            "status": job.status,

            "indexed_files": job.indexed_files,

            "total_files": job.total_files,

            "current_file": job.current_file,

            "progress": (
                0
                if job.total_files == 0
                else int(
                    job.indexed_files * 100
                    / job.total_files
                )
            ),

            "started_at": job.started_at,

            "completed_at": job.completed_at

        }

        for job in latest_jobs

    ]