"""The single indexing worker.

One thread for the whole process, one job at a time: the GPU models
(MiniLM, CLIP, Whisper, PaddleOCR) are shared, and running two jobs at once
would only make both slower and risk running out of GPU memory.

The loop claims the oldest queued job from Postgres, runs it, and always
finalizes it. Nothing that happens inside a job can kill the thread.
"""

import logging
import shutil
import threading
import time
import traceback
from collections.abc import Callable
from pathlib import Path

from app.core.config import settings
from app.core.timing import collecting
from app.database.db import SessionLocal
from app.platforms.errors import PlatformPreconditionError
from app.scheduler.context import JobContext
from app.scheduler.errors import sanitize_error
from app.scheduler.jobs import claim_next_job, finalize_job

logger = logging.getLogger("cogniseek.worker")

POLL_INTERVAL_SECONDS = 5.0

# Back-off after an unexpected error in the loop itself (e.g. DB down).
LOOP_ERROR_BACKOFF_SECONDS = 2.0


def default_platform_factories() -> dict[str, Callable[[], object]]:

    # Imported lazily: the platforms pull in the ML stack.
    from app.platforms.github.github_platform import GitHubPlatform
    from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform
    from app.platforms.local.local_platform import LocalPlatform

    return {
        "local": LocalPlatform,
        "google_drive": GoogleDrivePlatform,
        "github": GitHubPlatform
    }


def jobs_temp_root() -> Path:

    return Path(settings.TEMP_DIR) / "jobs"


def clear_orphaned_job_dirs() -> int:
    """At startup no job can be running, so any job temp dir is left over
    from a crash or a hard kill (where `finally` never ran)."""

    root = jobs_temp_root()

    if not root.is_dir():
        return 0

    removed = 0

    for child in root.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
            removed += 1

    return removed


class IndexingWorker:

    def __init__(
        self,
        platform_factories: dict[str, Callable[[], object]] | None = None,
        session_factory=SessionLocal,
        poll_interval: float = POLL_INTERVAL_SECONDS
    ):

        self._platform_factories = platform_factories
        self._session_factory = session_factory
        self._poll_interval = poll_interval

        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self.current_job_id = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_forever,
            name="indexing-worker",
            daemon=True
        )
        self._thread.start()

        logger.info("Indexing worker started.")

    def stop(self, timeout: float = 10.0) -> None:
        """Ask the loop to exit after the current job and wait for it."""

        self._stop.set()
        self._wake.set()

        if self._thread is not None:
            self._thread.join(timeout)

        logger.info("Indexing worker stopped.")

    def notify(self) -> None:
        """Called after enqueueing so the worker does not wait for the poll."""

        self._wake.set()

    @property
    def is_alive(self) -> bool:

        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def _run_forever(self) -> None:

        while not self._stop.is_set():

            try:
                ran = self.run_once()
            except Exception:
                # Never let the thread die (BUG-01). Log and back off.
                logger.exception("Indexing worker loop error")
                self._stop.wait(LOOP_ERROR_BACKOFF_SECONDS)
                continue

            if not ran:
                self._wake.wait(self._poll_interval)
                self._wake.clear()

    def run_once(self) -> bool:
        """Claim and run one job. Returns False when the queue is empty."""

        with self._session_factory() as db:
            job = claim_next_job(db)

            if job is None:
                return False

            job_id, user_id, platform_name = job.id, job.user_id, job.platform

        self._run_job(job_id, user_id, platform_name)

        return True

    def _platforms(self) -> dict[str, Callable[[], object]]:

        if self._platform_factories is None:
            self._platform_factories = default_platform_factories()

        return self._platform_factories

    def _run_job(self, job_id, user_id, platform_name: str) -> None:

        self.current_job_id = job_id

        temp_dir = jobs_temp_root() / str(job_id)

        context = JobContext(
            job_id=job_id,
            user_id=user_id,
            platform=platform_name,
            temp_dir=temp_dir,
            session_factory=self._session_factory
        )

        error_message = None

        logger.info("Job %s started: %s for user %s", job_id, platform_name, user_id)

        try:

            temp_dir.mkdir(parents=True, exist_ok=True)

            factory = self._platforms().get(platform_name)

            if factory is None:
                raise PlatformPreconditionError(f"Unknown platform '{platform_name}'.")

            with collecting(context.timer):
                factory().index(context)

        except PlatformPreconditionError as e:

            error_message = sanitize_error(e, context.allowed_roots, with_type=False)
            logger.warning("Job %s precondition failed: %s", job_id, error_message)

        except Exception as e:

            error_message = sanitize_error(e, context.allowed_roots)
            logger.error("Job %s crashed:\n%s", job_id, traceback.format_exc())

        finally:

            self._finish(context, error_message)

            shutil.rmtree(temp_dir, ignore_errors=True)

            self.current_job_id = None

    def _finish(self, context: JobContext, error_message: str | None) -> None:
        """Persist the last counters and the final status, whatever happened."""

        for attempt in range(3):
            try:
                context.flush()
                with self._session_factory() as db:
                    job = finalize_job(db, context.job_id, error_message)
                logger.info(
                    "Job %s finished: %s (%s ok, %s failed, %s skipped)",
                    job.id, job.status, job.succeeded_files, job.failed_files, job.skipped_files
                )
                return
            except Exception:
                logger.exception("Could not finalize job %s (attempt %s)", context.job_id, attempt + 1)
                time.sleep(0.5 * (attempt + 1))


# The process-wide worker (started from the FastAPI lifespan).
worker = IndexingWorker()


def notify_worker() -> None:

    worker.notify()
