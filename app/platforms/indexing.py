"""Shared per-file loop for platform indexing."""

import os
from typing import Callable, Iterable, TypeVar

from app.config.file_types import AUDIOS, DOCUMENTS, IMAGES, VIDEOS
from app.platforms.errors import PlatformPreconditionError


SUPPORTED_EXTENSIONS = frozenset(ext.lower() for ext in DOCUMENTS + IMAGES + AUDIOS + VIDEOS)

T = TypeVar("T")


def is_supported(name: str) -> bool:

    return os.path.splitext(name or "")[1].lower() in SUPPORTED_EXTENSIONS


def process_files(
    ctx,
    items: Iterable[T],
    file_ref: Callable[[T], str],
    handle: Callable[[int, T], None]
) -> None:
    """Run `handle` for every item; one failure never stops the others.

    - stops between files when the job is cancelled
    - PlatformPreconditionError (auth lost, rate limit) aborts the whole job
    - any other exception counts the file as failed and is recorded
    """

    for position, item in enumerate(items):

        if ctx.is_cancelled():
            break

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

    ctx.report_progress(force=True)
