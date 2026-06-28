import os
import pickle


def remove_from_index(index_file, filename):

    if not os.path.exists(index_file):
        return

    with open(index_file, "rb") as f:
        data = pickle.load(f)

    original_count = len(data)

    data = [
        item
        for item in data
        if item.get("file") != filename
    ]

    removed = original_count - len(data)

    with open(index_file, "wb") as f:
        pickle.dump(data, f)

    print(
        f"{removed} entries removed from {index_file}"
    )