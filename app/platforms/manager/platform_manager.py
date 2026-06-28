class PlatformManager:

    def __init__(self):

        self.platforms = {}

    def register(
        self,
        name,
        platform
    ):

        self.platforms[name] = platform

    def get(
        self,
        name
    ):

        return self.platforms.get(name)

    def all(self):

        return self.platforms.values()

    def index(
    self,
    name
    ):

        if name == "all":

         for platform in self.platforms.values():

            print(f"\nIndexing {platform.__class__.__name__}...")

            platform.index()

         return

        platform = self.get(name)

        if platform is None:

         raise ValueError(
            f"Platform '{name}' not found."
        )

        print(f"\nIndexing {name}...")

        platform.index()