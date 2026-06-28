from app.scheduler.status import (
    set_queue,
    set_priority,
    reset_status
)

platform_queue = []

current_platform = None

completed_platforms = []

def create_queue(priority, platforms):

    global platform_queue
    global completed_platforms

    reset_status()

    completed_platforms = []

    platform_queue = [priority]

    for platform in platforms:

        if platform != priority:
            platform_queue.append(platform)

    set_priority(priority)
    set_queue(platform_queue)


def get_next_platform():

    global platform_queue

    if len(platform_queue) == 0:
        return None

    platform = platform_queue.pop(0)

    set_queue(platform_queue)

    return platform


def mark_completed(platform):

    global completed_platforms

    completed_platforms.append(platform)


def get_completed():

    return completed_platforms


def get_queue():

    return platform_queue