"""Stage timing for indexing ("where the time went").

    with span("ocr"):
        ...

A span records its SELF time (its duration minus that of nested spans), so the
stages of a file add up to the file's total instead of double counting (e.g.
"extract_text" of a scanned PDF excludes the "pdf_render" and "ocr" spans inside
it). Spans are attributed to the active StageTimer and to the current file type.

Cost: two perf_counter() calls and a dict update per span - a few microseconds,
against stages that take milliseconds to minutes, so it stays on in production.
Without an active timer (search requests, tests) a span only measures and logs.

Context variables carry the timer, file type and span stack, so worker threads
started with contextvars.copy_context() (the indexing pipeline) report into the
job that started them.
"""

import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

logger = logging.getLogger("cogniseek.timing")

# Stages, in pipeline order (the Indexing Center shows them in this order).
STAGES = (
    "download", "extract_text", "pdf_render", "ocr", "audio_extract", "whisper",
    "frame_extract", "clip_image", "minilm", "qdrant_upsert", "ledger", "model_wait", "other",
)


class StageTimer:
    """Thread-safe totals: seconds and calls per stage, overall and per file type."""

    def __init__(self) -> None:

        self._lock = threading.Lock()
        self.seconds: dict[str, float] = {}
        self.calls: dict[str, int] = {}
        self.by_type: dict[str, dict[str, float]] = {}

    def add(self, stage: str, seconds: float, file_type: str | None = None) -> None:

        with self._lock:
            self.seconds[stage] = self.seconds.get(stage, 0.0) + seconds
            self.calls[stage] = self.calls.get(stage, 0) + 1
            if file_type:
                per_type = self.by_type.setdefault(file_type, {})
                per_type[stage] = per_type.get(stage, 0.0) + seconds

    def snapshot(self) -> dict:
        """JSON-ready totals (rounded to milliseconds) in STAGES order."""

        def ordered(values: dict[str, float]) -> dict[str, float]:
            keys = [s for s in STAGES if s in values] + sorted(k for k in values if k not in STAGES)
            return {k: round(values[k], 3) for k in keys}

        with self._lock:
            return {
                "seconds": ordered(self.seconds),
                "calls": {k: self.calls[k] for k in ordered(self.seconds)},
                "by_type": {t: ordered(v) for t, v in sorted(self.by_type.items())},
            }


_timer: ContextVar[StageTimer | None] = ContextVar("stage_timer", default=None)
_file_type: ContextVar[str | None] = ContextVar("stage_file_type", default=None)
_stack: ContextVar[tuple] = ContextVar("stage_stack", default=())


class _Frame:

    __slots__ = ("child",)

    def __init__(self) -> None:

        self.child = 0.0


@contextmanager
def span(stage: str) -> Iterator[None]:

    frame = _Frame()
    parents = _stack.get()
    token = _stack.set((*parents, frame))
    started = time.perf_counter()

    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        _stack.reset(token)
        if parents:
            parents[-1].child += elapsed
        own = max(0.0, elapsed - frame.child)
        timer = _timer.get()
        if timer is not None:
            timer.add(stage, own, _file_type.get())
        logger.debug("span %s %.3fs (self %.3fs)", stage, elapsed, own)


@contextmanager
def collecting(timer: StageTimer) -> Iterator[StageTimer]:
    """Attribute every span in this context (and contexts copied from it) to `timer`."""

    token = _timer.set(timer)
    try:
        yield timer
    finally:
        _timer.reset(token)


@contextmanager
def file_scope(file_type: str | None) -> Iterator[None]:
    """Spans inside count towards this file type; time not covered by a stage is 'other'."""

    token = _file_type.set(file_type)
    try:
        with span("other"):
            yield
    finally:
        _file_type.reset(token)


@contextmanager
def waiting_for(lock) -> Iterator[None]:
    """Hold a shared model lock; the time spent waiting for it is recorded as
    "model_wait" instead of inflating the stage that wanted the model (several
    files are processed at once, but each model runs one call at a time)."""

    with span("model_wait"):
        lock.acquire()
    try:
        yield
    finally:
        lock.release()


def current_timer() -> StageTimer | None:

    return _timer.get()


def stage_names() -> list[str]:

    return list(STAGES)
