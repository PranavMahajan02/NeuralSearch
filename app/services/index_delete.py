import os
from app.services.pickle_store import dump_pickle_atomic, load_pickle


def remove_from_index(index_file, filename):

    if not os.path.exists(index_file):
        return

    data = load_pickle(index_file)

    original_count = len(data)

    data = [
        item
        for item in data
        if item.get("file") != filename
    ]

    removed = original_count - len(data)

    dump_pickle_atomic(index_file, data)

    print(
        f"{removed} entries removed from {index_file}"
    )