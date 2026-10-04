_cancelled_users = set()


def cancel_job(user_id):

    _cancelled_users.add(str(user_id))


def clear_cancel(user_id):

    _cancelled_users.discard(str(user_id))


def is_cancelled(user_id):

    return str(user_id) in _cancelled_users