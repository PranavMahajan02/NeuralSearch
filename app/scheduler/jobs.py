"""Indexing jobs stored in Postgres.

State machine (every other transition is a bug):

    queued  -> running     worker claims it (SELECT ... FOR UPDATE SKIP LOCKED)
    queued  -> cancelled   user cancels it, cancels the running job, or logs out
    running -> completed               no file failed
    running -> completed_with_errors   some files failed, some succeeded
    running -> failed                  precondition/exception, or every file failed
    running -> cancelled               cancel_requested was set while running
    running -> failed                  server restarted mid-run (startup recovery)

completed / completed_with_errors / failed / cancelled are final.
"""

from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import (
    ACTIVE_JOB_STATUSES,
    IndexingJob,
    IndexingJobError
)


INTERRUPTED_MESSAGE = "Interrupted by server restart"


class ActiveJobExists(Exception):

    def __init__(self, platforms: List[str]):

        super().__init__(", ".join(platforms))
        self.platforms = platforms


# ----------------------------------------------------------------------
# Enqueue
# ----------------------------------------------------------------------

def active_platforms(db: Session, user_id, platforms: Iterable[str]) -> List[str]:

    rows = (
        db.query(IndexingJob.platform)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.platform.in_(list(platforms)),
            IndexingJob.status.in_(ACTIVE_JOB_STATUSES)
        )
        .all()
    )

    return sorted({row.platform for row in rows})


def enqueue_jobs(db: Session, user_id, priority_platform: str, platforms: List[str]) -> List[IndexingJob]:
    """Create one NEW queued job per platform, priority platform first.

    Raises ActiveJobExists (-> 409) if any platform already has a queued or
    running job; nothing is created in that case. A partial unique index
    (uq_indexing_jobs_one_active) makes this race-free.
    """

    ordered = [priority_platform] + [p for p in platforms if p != priority_platform]

    conflicts = active_platforms(db, user_id, ordered)

    if conflicts:
        raise ActiveJobExists(conflicts)

    # Explicit, strictly increasing created_at so the priority platform is
    # claimed first even within one transaction.
    base = datetime.utcnow()

    jobs = [
        IndexingJob(
            user_id=user_id,
            platform=platform,
            status="queued",
            created_at=base + timedelta(microseconds=position),
            current_file=""
        )
        for position, platform in enumerate(ordered)
    ]

    db.add_all(jobs)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ActiveJobExists(active_platforms(db, user_id, ordered) or ordered)

    for job in jobs:
        db.refresh(job)

    return jobs


# ----------------------------------------------------------------------
# Worker side
# ----------------------------------------------------------------------

def claim_next_job(db: Session) -> Optional[IndexingJob]:
    """Atomically move the oldest queued job to running.

    FOR UPDATE SKIP LOCKED: a second worker (or process) skips the row this
    one is claiming instead of blocking on it or claiming it twice.
    """

    job = (
        db.query(IndexingJob)
        .filter(IndexingJob.status == "queued")
        .order_by(IndexingJob.created_at, IndexingJob.id)
        .with_for_update(skip_locked=True)
        .first()
    )

    if job is None:
        db.rollback()
        return None

    now = datetime.utcnow()

    job.status = "running"
    job.started_at = now
    job.heartbeat_at = now
    job.completed_at = None
    job.error_message = None

    db.commit()
    db.refresh(job)

    return job


def final_status(job: IndexingJob, error_message: Optional[str]) -> str:

    if job.cancel_requested:
        return "cancelled"

    if error_message:
        return "failed"

    if job.failed_files == 0:
        return "completed"

    if job.succeeded_files > 0:
        return "completed_with_errors"

    return "failed"


def finalize_job(db: Session, job_id, error_message: Optional[str] = None) -> IndexingJob:
    """Set the final status from the stored counters. Counters are never
    overwritten here (the old code forced indexed_files = total_files)."""

    job = db.get(IndexingJob, job_id, with_for_update=True)

    status = final_status(job, error_message)

    if status == "failed" and not error_message:
        error_message = f"All {job.failed_files} files failed to index."

    if status == "cancelled" and not error_message:
        error_message = "Cancelled by user."

    job.status = status
    job.error_message = error_message
    job.completed_at = datetime.utcnow()
    job.heartbeat_at = job.completed_at
    job.current_file = ""

    if status in ("completed", "completed_with_errors"):
        job.last_index_time = job.completed_at

    db.commit()
    db.refresh(job)

    return job


def recover_interrupted_jobs(db: Session) -> int:
    """On boot: a job still 'running' was cut off by a restart -> failed.
    Queued jobs stay queued and are picked up by the worker."""

    count = (
        db.query(IndexingJob)
        .filter(IndexingJob.status == "running")
        .update(
            {
                IndexingJob.status: "failed",
                IndexingJob.error_message: INTERRUPTED_MESSAGE,
                IndexingJob.completed_at: datetime.utcnow()
            },
            synchronize_session=False
        )
    )

    db.commit()

    return count


# ----------------------------------------------------------------------
# Cancel
# ----------------------------------------------------------------------

def _cancel_queued(db: Session, user_id) -> int:

    return (
        db.query(IndexingJob)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.status == "queued"
        )
        .update(
            {
                IndexingJob.status: "cancelled",
                IndexingJob.cancel_requested: True,
                IndexingJob.error_message: "Cancelled by user.",
                IndexingJob.completed_at: datetime.utcnow()
            },
            synchronize_session=False
        )
    )


def _flag_running(db: Session, user_id) -> int:

    return (
        db.query(IndexingJob)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.status == "running"
        )
        .update(
            {IndexingJob.cancel_requested: True},
            synchronize_session=False
        )
    )


def request_cancel(db: Session, job: IndexingJob) -> IndexingJob:
    """Cancel one job of the user.

    queued  -> cancelled immediately.
    running -> cancel_requested; the platform stops after the current file.
               Cancelling the running job also cancels the user's queued jobs.
    final   -> no-op.
    """

    if job.status == "queued":
        job.status = "cancelled"
        job.cancel_requested = True
        job.error_message = "Cancelled by user."
        job.completed_at = datetime.utcnow()

    elif job.status == "running":
        job.cancel_requested = True
        _cancel_queued(db, job.user_id)

    db.commit()
    db.refresh(job)

    return job


def cancel_user_jobs(db: Session, user_id) -> None:
    """Logout: cancel every queued job and ask the running one to stop."""

    _cancel_queued(db, user_id)
    _flag_running(db, user_id)
    db.commit()


# ----------------------------------------------------------------------
# Read side
# ----------------------------------------------------------------------

def latest_jobs_per_platform(db: Session, user_id) -> List[IndexingJob]:

    newest = (
        db.query(
            IndexingJob.platform,
            func.max(IndexingJob.created_at).label("created_at")
        )
        .filter(IndexingJob.user_id == user_id)
        .group_by(IndexingJob.platform)
        .subquery()
    )

    return (
        db.query(IndexingJob)
        .join(
            newest,
            (IndexingJob.platform == newest.c.platform)
            & (IndexingJob.created_at == newest.c.created_at)
        )
        .filter(IndexingJob.user_id == user_id)
        .order_by(IndexingJob.platform)
        .all()
    )


def indexed_platforms(db: Session, user_id) -> List[str]:
    """Platforms with at least one successful run, whatever is running now."""

    rows = (
        db.query(IndexingJob.platform)
        .filter(
            IndexingJob.user_id == user_id,
            IndexingJob.status.in_(("completed", "completed_with_errors"))
        )
        .distinct()
        .all()
    )

    return sorted(row.platform for row in rows)


def get_user_job(db: Session, user_id, job_id) -> Optional[IndexingJob]:

    job = db.get(IndexingJob, job_id)

    if job is None or str(job.user_id) != str(user_id):
        return None

    return job


def job_errors(db: Session, job_id, limit: int = 200) -> List[IndexingJobError]:

    return (
        db.query(IndexingJobError)
        .filter(IndexingJobError.job_id == job_id)
        .order_by(IndexingJobError.created_at, IndexingJobError.id)
        .limit(limit)
        .all()
    )


def serialize_job(job: IndexingJob) -> dict:

    total = job.total_files or 0
    processed = job.processed_files or 0

    return {
        "id": str(job.id),
        "platform": job.platform,
        "status": job.status,
        "total_files": total,
        "processed_files": processed,
        "succeeded_files": job.succeeded_files or 0,
        "failed_files": job.failed_files or 0,
        "skipped_files": job.skipped_files or 0,
        "downloaded_files": job.downloaded_files or 0,
        # Kept for older clients: same value as processed_files.
        "indexed_files": processed,
        "progress": 0 if total == 0 else min(100, int(processed * 100 / total)),
        "current_file": job.current_file or "",
        "error_message": job.error_message,
        "cancel_requested": bool(job.cancel_requested),
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "heartbeat_at": job.heartbeat_at
    }
