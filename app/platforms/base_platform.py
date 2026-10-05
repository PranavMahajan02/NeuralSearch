from abc import ABC, abstractmethod


class BasePlatform(ABC):
    """An indexing source. Search and open do not go through platforms any
    more: search is one user-scoped query per modality (search_service) and
    open is resolved from the indexed_files ledger (open_service)."""

    @abstractmethod
    def index(self, ctx):
        """Index the user's files. `ctx` is an app.scheduler.context.JobContext:
        report progress and per-file errors through it, and stop between files
        when ctx.is_cancelled() is True. Raise PlatformPreconditionError when
        the platform cannot run at all."""

    @abstractmethod
    def list_files(self, *args, **kwargs):
        pass
