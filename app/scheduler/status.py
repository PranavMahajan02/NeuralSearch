status = {
    "user_id": None,
    "current_platform": None,
    "completed_platforms": [],
    "queue": [],
    "worker_running": False,
    "priority_platform": None,
    "priority_completed": False
}


def set_owner(user_id):
    status["user_id"] = user_id


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

def get_status_for_user(user_id):
    """The queue is still global (per-user queues are Phase 2): only its
    owner sees its state; everyone else gets an idle status."""

    if status["user_id"] is not None and str(status["user_id"]) == str(user_id):
        return {key: value for key, value in status.items() if key != "user_id"}

    return {
        "current_platform": None,
        "completed_platforms": [],
        "queue": [],
        "worker_running": False,
        "priority_platform": None,
        "priority_completed": False
    }


def reset_status():
    status["user_id"] = None

    status["current_platform"] = None
    status["completed_platforms"] = []
    status["queue"] = []
    status["worker_running"] = False
    status["priority_platform"] = None
    status["priority_completed"] = False