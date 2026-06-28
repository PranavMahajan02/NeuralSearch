import threading

from app.scheduler.scheduler import run_scheduler
from app.scheduler.status import set_worker_running

worker_thread = None


def start_worker():

    global worker_thread

    if (
        worker_thread is not None
        and worker_thread.is_alive()
    ):
        print("Worker already running.")
        return

    set_worker_running(True)

    worker_thread = threading.Thread(
        target=run_scheduler,
        daemon=True
    )

    worker_thread.start()

    print("Background worker started.")