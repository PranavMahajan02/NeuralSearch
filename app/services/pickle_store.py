"""Atomic, lock-protected access to the pickle indexes.

Writes go to <file>.tmp and are swapped in with os.replace, under one
module-level lock that readers also take, so a search never reads a
half-written pickle. (Windows cannot replace a file another handle has open,
which is why readers take the lock too.) Phase 3 removes the pickles.
"""

import os
import pickle
import threading
import time


PICKLE_LOCK = threading.RLock()

_REPLACE_RETRIES = 20


def load_pickle(path, default=None):

    with PICKLE_LOCK:

        if not os.path.exists(path):
            return [] if default is None else default

        with open(path, "rb") as f:
            return pickle.load(f)


def dump_pickle_atomic(path, data):

    tmp_path = f"{path}.tmp"

    with PICKLE_LOCK:

        with open(tmp_path, "wb") as f:
            pickle.dump(data, f)
            f.flush()
            os.fsync(f.fileno())

        # Another process (antivirus, indexer) may briefly hold the target.
        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError:
                if attempt == _REPLACE_RETRIES - 1:
                    os.remove(tmp_path)
                    raise
                time.sleep(0.05)
