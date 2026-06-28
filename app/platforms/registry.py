from app.platforms.manager.platform_manager import PlatformManager

from app.platforms.local.local_platform import LocalPlatform
from app.config.local_config import load_local_folders

from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform
from app.platforms.github.github_platform import GitHubPlatform


platform_manager = PlatformManager()


platform_manager.register(
    "local",
    LocalPlatform(
        folders=load_local_folders()
    )
)


platform_manager.register(
    "google_drive",
    GoogleDrivePlatform()
)


platform_manager.register(
    "github",
    GitHubPlatform()
)