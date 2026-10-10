"""Shared per-file loop for platform indexing."""

import os
from collections.abc import Callable, Iterable
from typing import TypeVar

from app.config.file_types import AUDIOS, DOCUMENTS, IMAGES, VIDEOS
from app.platforms.errors import PlatformPreconditionError

SUPPORTED_EXTENSIONS = frozenset(ext.lower() for ext in DOCUMENTS + IMAGES + AUDIOS + VIDEOS)

T = TypeVar("T")


EXCLUDED_REASON = "excluded"


def exclude_globs() -> list:
    """settings.INDEX_EXCLUDE_GLOBS as a lower-case list (generated/noise files)."""

    from app.core.config import settings

    return [g.strip().lower() for g in settings.INDEX_EXCLUDE_GLOBS.split(",") if g.strip()]


def is_excluded(name: str) -> bool:
    """True when the file's base name matches one of INDEX_EXCLUDE_GLOBS
    (case-insensitive). Excluded files are recorded as 'excluded' and never
    downloaded or indexed, by every connector."""

    import fnmatch

    base = os.path.basename((name or "").replace("\\", "/")).lower()

    return any(fnmatch.fnmatchcase(base, glob) for glob in exclude_globs())


def is_supported(name: str) -> bool:

    return os.path.splitext(name or "")[1].lower() in SUPPORTED_EXTENSIONS


# Fast, small work first: a new user can search documents within seconds while
# the videos are still being processed (time-to-first-search; the total is the same).
TYPE_ORDER = {"document": 0, "image": 1, "audio": 2, "video": 3}


def schedule_key(file_type: str | None, size: int | None, ref: str):
    """Deterministic order: documents/code -> images -> audio -> video, then by size, then name."""

    return (TYPE_ORDER.get(file_type or "", 4), size if size is not None else 0, ref)


def process_files[T](
    ctx,
    items: Iterable[T],
    file_ref: Callable[[T], str],
    handle: Callable[[int, T], None],
    workers: int | None = None,
    prefetch: int | None = None,
) -> None:
    """Run `handle` for every item; one failure never stops the others.

    - up to `workers` files are processed at once (settings.INDEX_IO_WORKERS):
      downloads and CPU extraction of one file overlap with another file's GPU
      work; the GPU sections stay serialized by the model locks
    - at most `prefetch` files are in flight (settings.INDEX_PREFETCH, >= workers),
      so memory and temp disk stay bounded
    - stops starting new files when the job is cancelled (files already running
      finish; nothing is left half-written)
    - PlatformPreconditionError (auth lost, rate limit) aborts the whole job
    - any other exception counts the file as failed and is recorded
    """

    from app.core.config import settings

    workers = settings.INDEX_IO_WORKERS if workers is None else workers
    prefetch = settings.INDEX_PREFETCH if prefetch is None else prefetch

    def run(position: int, item: T) -> None:

        ref = file_ref(item)
        ctx.start_file(ref)

        try:
            handle(position, item)
        except PlatformPreconditionError:
            raise
        except Exception as error:
            ctx.file_failed(ref, error)
        else:
            ctx.file_succeeded()

    if workers <= 1:
        for position, item in enumerate(items):
            if ctx.is_cancelled():
                break
            run(position, item)
        ctx.report_progress(force=True)
        return

    import contextvars
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

    window = max(workers, prefetch)
    pending = set()
    abort: BaseException | None = None
    queue = iter(enumerate(items))
    exhausted = False

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="index-io") as pool:
        while True:
            while not exhausted and abort is None and len(pending) < window:
                if ctx.is_cancelled():
                    exhausted = True
                    break
                try:
                    position, item = next(queue)
                except StopIteration:
                    exhausted = True
                    break
                # copy_context: stage timings of the worker thread go to this job.
                pending.add(pool.submit(contextvars.copy_context().run, run, position, item))

            if not pending:
                break

            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                error = future.exception()
                if isinstance(error, PlatformPreconditionError) and abort is None:
                    abort = error
                elif error is not None and abort is None:
                    abort = error  # a bug in the loop itself: fail the job, as before

    ctx.report_progress(force=True)

    if abort is not None:
        raise abort
