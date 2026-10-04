from sqlalchemy.orm import Session
from datetime import datetime

from app.database.db import SessionLocal
from app.database.models import IndexingJob

from app.scheduler.cancel import (
    is_cancelled,
    clear_cancel
)

from app.scheduler.status import (
    set_current,
    add_completed,
    mark_priority_completed,
    get_status,
    set_worker_running
)

from app.scheduler.queue import (
    get_next_platform,
    mark_completed
)

from app.platforms.local.local_platform import LocalPlatform
from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform
from app.platforms.github.github_platform import GitHubPlatform


def run_scheduler():

    while True:

        job = get_next_platform()

        if job is None:

            print("Queue completed.")

            set_worker_running(False)
            set_current(None)

            break

        platform = job["platform"]
        user_id = job["user_id"]

        # ----------------------------------------
        # Mark this platform as INDEXING
        # ----------------------------------------

        try:

            db: Session = SessionLocal()

            db_job = (

                db.query(IndexingJob)

                .filter(

                    IndexingJob.user_id == user_id,

                    IndexingJob.platform == platform,

                )

                .order_by(IndexingJob.started_at.desc())

                .first()

            )

            if db_job:

                db_job.status = "indexing"

                db.commit()

        finally:

            db.close()

        # ----------------------------------------

        if is_cancelled(user_id):

            print(f"Cancelled indexing for user {user_id}")

            clear_cancel(user_id)

            mark_completed(platform)

            continue

        set_current(platform)

        print(f"Indexing {platform}...")

        if platform == "local":

            LocalPlatform().index(
                user_id
            )

        elif platform == "google_drive":

            GoogleDrivePlatform().index(
                user_id
            )

        elif platform == "github":

            GitHubPlatform().index(
                user_id
            )

        # Google Photos later

        mark_completed(platform)

        add_completed(platform)

        # ----------------------------------------
        # Mark platform as COMPLETED
        # ----------------------------------------

        try:

            db: Session = SessionLocal()

            db_job = (

                db.query(IndexingJob)

                .filter(

                    IndexingJob.user_id == user_id,

                    IndexingJob.platform == platform,

                )

                .order_by(IndexingJob.started_at.desc())

                .first()

            )

            if db_job:

                db_job.status = "completed"

                db_job.completed_at = datetime.utcnow()

                db_job.indexed_files = db_job.total_files

                db.commit()

        finally:

            db.close()

        # ----------------------------------------

        if platform == get_status()["priority_platform"]:

            mark_priority_completed()

        print(f"{platform} completed.")