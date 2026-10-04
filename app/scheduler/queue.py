from app.scheduler.status import (
    set_queue,
    set_priority,
    reset_status
)

platform_queue = []

completed_platforms = []


def create_queue(
    user_id,
    priority,
    platforms
):

    global platform_queue
    global completed_platforms

    reset_status()

    completed_platforms = []

    platform_queue = []

    # Priority first
    platform_queue.append({

        "user_id": user_id,

        "platform": priority

    })

    # Remaining platforms
    for platform in platforms:

        if platform == priority:
            continue

        platform_queue.append({

            "user_id": user_id,

            "platform": platform

        })

    set_priority(priority)

    set_queue(
        [item["platform"] for item in platform_queue]
    )


def get_next_platform():

    global platform_queue

    if len(platform_queue) == 0:
        return None

    item = platform_queue.pop(0)

    set_queue(
        [i["platform"] for i in platform_queue]
    )

    return item


def mark_completed(platform):

    global completed_platforms

    completed_platforms.append(platform)


def get_completed():

    return completed_platforms


def get_queue():

    return platform_queue