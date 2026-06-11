import time
import subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileWatcher(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        print(f"\nNew file detected: {event.src_path}")

        print("Running index.py...")

        subprocess.run(
            ["python", "index.py"]
        )

        print("Index updated!")


folder_to_watch = "data"

observer = Observer()

observer.schedule(
    FileWatcher(),
    folder_to_watch,
    recursive=False
)

observer.start()

print(f"Watching folder: {folder_to_watch}")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:

    observer.stop()

observer.join()