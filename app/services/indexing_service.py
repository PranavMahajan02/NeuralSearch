from sqlalchemy.orm import Session
from datetime import datetime

from app.database.models import IndexingJob


def get_job(db: Session, user_id, platform):

    return (
        db.query(IndexingJob)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.platform == platform
        )
        .order_by(IndexingJob.started_at.desc())
        .first()
    )


def mark_index_started(db: Session, user_id, platform):

    job = get_job(db, user_id, platform)

    if job is None:

        job = IndexingJob(
            user_id=user_id,
            platform=platform
        )

        db.add(job)

    job.status = "indexing"
    job.started_at = datetime.utcnow()
    job.indexed_files = 0
    job.total_files = 0
    job.current_file = ""
    job.completed_at = None

    db.commit()


def mark_index_completed(
    db: Session,
    user_id,
    platform,
    total_files
):

    job = get_job(db, user_id, platform)

    if job is None:

        job = IndexingJob(
            user_id=user_id,
            platform=platform
        )

        db.add(job)

    job.status = "completed"
    job.total_files = total_files
    job.indexed_files = total_files
    job.completed_at = datetime.utcnow()
    job.last_index_time = datetime.utcnow()

    db.commit()


def user_has_indexed(db: Session, user_id):

    return (
        db.query(IndexingJob)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.status == "completed"
        )
        .count()
    ) > 0