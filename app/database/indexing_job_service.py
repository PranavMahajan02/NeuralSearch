from sqlalchemy.orm import Session

from app.database.models import IndexingJob


def get_latest_job(
    db: Session,
    user_id,
    platform
):

    return (

        db.query(IndexingJob)

        .filter(

            IndexingJob.user_id == user_id,

            IndexingJob.platform == platform

        )

        .order_by(

            IndexingJob.started_at.desc()

        )

        .first()

    )


def set_total_files(
    db: Session,
    user_id,
    platform,
    total
):

    job = get_latest_job(

        db,

        user_id,

        platform

    )

    if job is None:

        print(
            f"[DB] No indexing job found for {platform}"
        )

        return

    job.total_files = total

    db.commit()

    db.refresh(job)

    print(
        f"[DB] Total files updated: {job.total_files}"
    )


def increment_indexed_files(
    db,
    user_id,
    platform
):

    job = get_latest_job(
        db,
        user_id,
        platform
    )

    if job is None:
        print("NO JOB FOUND")
        return

    job.indexed_files += 1

    print(
        f"Updating progress: {job.indexed_files}/{job.total_files}"
    )

    db.commit()
    db.refresh(job)

    print(
        f"Saved to DB: {job.indexed_files}/{job.total_files}"
    )

def update_current_file(
    db: Session,
    user_id,
    platform,
    filename
):

    job = get_latest_job(
        db,
        user_id,
        platform
    )

    if job is None:
        return

    job.current_file = filename

    db.commit()