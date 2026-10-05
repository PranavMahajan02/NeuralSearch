class PlatformManager:
    """Registry of platform instances used by search and open.

    Indexing does not go through here: it runs as jobs in
    app/scheduler/worker.py (the old index() method could not work - BUG-13).
    """

    def __init__(self):

        self.platforms = {}

    def register(self, name, platform):

        self.platforms[name] = platform

    def get(self, name):

        return self.platforms.get(name)

    def all(self):

        return self.platforms.values()
