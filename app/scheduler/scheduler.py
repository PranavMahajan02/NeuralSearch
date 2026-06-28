from app.scheduler.status import (
    set_current,
    add_completed,
    mark_priority_completed,
    get_status,
    set_worker_running
)

from app.scheduler.queue import (
    get_next_platform,
    mark_completed
)

from app.platforms.local.local_platform import LocalPlatform
from app.platforms.google_drive.google_drive_platform import GoogleDrivePlatform
from app.platforms.github.github_platform import GitHubPlatform

def run_scheduler():

    while True:

        platform = get_next_platform()
        set_current(platform)

        if platform is None:
            print("Queue completed.")
            set_worker_running(False)
            set_current(None)
            break

        print(f"Indexing {platform}...")

        if platform == "local":

            LocalPlatform().index()

        elif platform == "google_drive":

            GoogleDrivePlatform().index()

        elif platform == "github":

            GitHubPlatform().index()        

        # Google Photos later
        # GitHub later

        mark_completed(platform)
        add_completed(platform)

        if platform == get_status()["priority_platform"]:
            mark_priority_completed()

        print(f"{platform} completed.")