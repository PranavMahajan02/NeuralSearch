"""JobContext: everything a platform needs while indexing one job.

Platforms never touch the job row directly. They report through the context,
which batches counter writes (at most every second or every 10 files) and
stores per-file errors (capped per job).
"""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.database.db import SessionLocal
from app.database.models import IndexingJob, IndexingJobError
from app.scheduler.errors import sanitize_error


logger = logging.getLogger("cogniseek.jobs")

MAX_STORED_ERRORS = 200

FLUSH_INTERVAL_SECONDS = 1.0

FLUSH_EVERY_N_FILES = 10


class JobContext:

    def __init__(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        platform: str,
        temp_dir: Path,
        session_factory=SessionLocal,
        clock=time.monotonic
    ):

        self.job_id = job_id
        self.user_id = user_id
        self.platform = platform
        self.temp_dir = Path(temp_dir)

        # Paths that may appear in stored error messages (the user's own scope).
        self.allowed_roots = [self.temp_dir]

        self._session_factory = session_factory
        self._clock = clock

        self.total_files = 0
        self.succeeded_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.downloaded_files = 0
        self.current_file = ""
        self.stored_errors = 0

        self._dirty_files = 0
        self._last_flush = clock()

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    @property
    def processed_files(self) -> int:

        return self.succeeded_files + self.failed_files

    def set_total(self, total: int) -> None:
        """Number of supported files that will be processed."""

        self.total_files = int(total)
        self.flush()

    def add_skipped(self, count: int = 1) -> None:
        """Folders and unsupported files: counted, not part of progress."""

        self.skipped_files += count
        self._maybe_flush()

    def start_file(self, file_ref: str) -> None:

        self.current_file = str(file_ref)[:500]

        # Time-based only: a slow file (e.g. a video) still shows up in the UI
        # within about a second instead of at the next 10-file boundary.
        if self._clock() - self._last_flush >= FLUSH_INTERVAL_SECONDS:
            self.flush()

    def file_downloaded(self) -> None:
        """A remote file was fetched (0 on a run where nothing changed)."""

        self.downloaded_files += 1

    def file_succeeded(self) -> None:

        self.succeeded_files += 1
        self._dirty_files += 1
        self._maybe_flush()

    def file_failed(self, file_ref: str, error: BaseException) -> None:

        self.failed_files += 1
        self._dirty_files += 1
        self.record_error(file_ref, error)
        self._maybe_flush()

    def report_progress(self, force: bool = False) -> None:

        if force:
            self.flush()
        else:
            self._maybe_flush()

    # ------------------------------------------------------------------
    # Errors
    # ------------------------------------------------------------------

    def record_error(self, file_ref: str, error: BaseException) -> None:

        logger.warning(
            "Job %s: failed on %s",
            self.job_id,
            file_ref,
            exc_info=(type(error), error, error.__traceback__)
        )

        if self.stored_errors >= MAX_STORED_ERRORS:
            return

        message = sanitize_error(error, allowed_roots=self.allowed_roots,
                                 with_type=not getattr(error, "user_facing", False))

        with self._session_factory() as db:
            db.add(
                IndexingJobError(
                    job_id=self.job_id,
                    file_ref=str(file_ref)[:1000],
                    error=message
                )
            )
            db.commit()

        self.stored_errors += 1

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def is_cancelled(self) -> bool:
        """Checked by platforms between files (one cheap SELECT)."""

        with self._session_factory() as db:
            requested = db.query(IndexingJob.cancel_requested).filter(
                IndexingJob.id == self.job_id
            ).scalar()

        return bool(requested)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _maybe_flush(self) -> None:

        if (
            self._dirty_files >= FLUSH_EVERY_N_FILES
            or self._clock() - self._last_flush >= FLUSH_INTERVAL_SECONDS
        ):
            self.flush()

    def flush(self) -> None:

        with self._session_factory() as db:
            db.query(IndexingJob).filter(IndexingJob.id == self.job_id).update(
                {
                    IndexingJob.total_files: self.total_files,
                    IndexingJob.processed_files: self.processed_files,
                    IndexingJob.succeeded_files: self.succeeded_files,
                    IndexingJob.failed_files: self.failed_files,
                    IndexingJob.skipped_files: self.skipped_files,
                    IndexingJob.downloaded_files: self.downloaded_files,
                    # Legacy column, kept equal to processed_files for old clients.
                    IndexingJob.indexed_files: self.processed_files,
                    IndexingJob.current_file: self.current_file,
                    IndexingJob.heartbeat_at: datetime.utcnow()
                },
                synchronize_session=False
            )
            db.commit()

        self._dirty_files = 0
        self._last_flush = self._clock()

    def file_dir(self, index: int) -> Path:
        """A fresh sub-directory of the job temp dir for one download."""

        path = self.temp_dir / f"{index:06d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def frames_dir(self) -> Path:

        return self.temp_dir / "frames"
