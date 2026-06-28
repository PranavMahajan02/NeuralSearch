status = {
    "current_platform": None,
    "completed_platforms": [],
    "queue": [],
    "worker_running": False,
    "priority_platform": None,
    "priority_completed": False
}


def set_current(platform):

    status["current_platform"] = platform


def set_queue(queue):

    status["queue"] = list(queue)


def add_completed(platform):

    status["completed_platforms"].append(platform)


def set_worker_running(value):

    status["worker_running"] = value


def set_priority(platform):

    status["priority_platform"] = platform


def mark_priority_completed():

    status["priority_completed"] = True


def get_status():

    return status

def reset_status():

    status["current_platform"] = None
    status["completed_platforms"] = []
    status["queue"] = []
    status["worker_running"] = False
    status["priority_platform"] = None
    status["priority_completed"] = False