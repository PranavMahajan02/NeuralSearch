from abc import ABC, abstractmethod


class BasePlatform(ABC):

    @abstractmethod
    def index(self, ctx):
        """Index the user's files. `ctx` is an app.scheduler.context.JobContext:
        report progress and per-file errors through it, and stop between files
        when ctx.is_cancelled() is True. Raise PlatformPreconditionError when
        the platform cannot run at all."""

    @abstractmethod
    def search(self, query, search_type="all"):
        pass

    @abstractmethod
    def upload(self, file_path):
        pass

    @abstractmethod
    def delete(self, file_name):
        pass

    @abstractmethod
    def list_files(self, *args, **kwargs):
        pass
