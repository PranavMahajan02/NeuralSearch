"""Read-only Drive download dry-run (no indexing, no ledger writes).

    venv\\Scripts\\python scripts\\drive_download_dryrun.py --email you@example.com [--workers 4]

Lists the user's Drive with the connector's own client, picks the files the
sync would fetch (fetchable, supported type, not excluded, under MAX_DOWNLOAD_MB;
the ledger is ignored, so EVERY eligible file is downloaded), and downloads them
through the parallel pipeline into a temp dir, deleting each file right away.

Prints counts and error types only - no file names or contents. The only write
is the one the app itself makes: a refreshed OAuth token is saved (encrypted).
"""

import argparse
import collections
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("PRELOAD_MODELS", "false")


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    from app.config.file_types import file_type_for
    from app.core.config import settings
    from app.database.db import SessionLocal
    from app.database.models import User
    from app.platforms.google_drive.drive_service import client_for_user
    from app.platforms.google_drive.google_drive_platform import local_extension
    from app.platforms.indexing import is_excluded, process_files

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == args.email.strip().lower()).one()
        user_id = user.id

    started = time.perf_counter()
    client = client_for_user(user_id)
    files, complete = client.list_files()

    eligible, skipped = [], collections.Counter()
    for file in files:
        extension = local_extension(file)
        size = int(file["size"]) if str(file.get("size") or "").isdigit() else None
        if extension is None:
            skipped["not fetchable"] += 1
        elif is_excluded(file.get("name", "")):
            skipped["excluded"] += 1
        elif file_type_for(f"x{extension}") is None:
            skipped["unsupported"] += 1
        elif size is not None and size > settings.max_download_bytes:
            skipped["too large"] += 1
        else:
            eligible.append((file, extension))

    lock = threading.Lock()
    stats = {"ok": 0, "bytes": 0}
    errors = collections.Counter()

    class Ctx:
        def is_cancelled(self):
            return False

        def start_file(self, ref):
            pass

        def file_succeeded(self):
            with lock:
                stats["ok"] += 1

        def file_failed(self, ref, error):
            with lock:
                errors[type(error).__name__] += 1

        def report_progress(self, force=False):
            pass

    with tempfile.TemporaryDirectory(prefix="drive-dryrun-") as tmp:

        def handle(position, item):
            file, extension = item
            target = Path(tmp) / f"{position:05d}{extension}"
            try:
                path = Path(client.download(file, target))
                with lock:
                    stats["bytes"] += path.stat().st_size
            finally:
                target.unlink(missing_ok=True)

        process_files(
            Ctx(), eligible, lambda item: item[0]["id"], handle, workers=args.workers, prefetch=max(8, args.workers)
        )
        leftover = sum(1 for _ in Path(tmp).iterdir())

    client.save_if_refreshed()

    print(f"listed {len(files)} (complete={complete}); eligible {len(eligible)}; skipped {dict(skipped)}")
    print(
        f"workers {args.workers}: downloaded {stats['ok']}/{len(eligible)}, "
        f"{stats['bytes'] / 1e6:.1f} MB, errors {sum(errors.values())} {dict(errors)}, "
        f"temp files left {leftover}, {time.perf_counter() - started:.1f}s"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
