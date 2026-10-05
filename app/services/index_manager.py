import os
import pickle

from app.services.pickle_store import dump_pickle_atomic, load_pickle
from app.cache.search_cache import (
    reload_document_cache,
    reload_image_cache,
    reload_audio_cache,
    reload_video_cache,
)

from app.config.file_types import (
    DOCUMENTS,
    IMAGES,
    AUDIOS,
    VIDEOS
)

def get_index_file(file_path):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension in DOCUMENTS:
        return "index.pkl"

    elif extension in IMAGES:
        return "image_index.pkl"

    elif extension in AUDIOS:
        return "audio_index.pkl"

    elif extension in VIDEOS:
        return "video_index.pkl"
        
    return None


def load_index(file_path):

    index_file = get_index_file(file_path)

    if index_file is None:
        return []

    return load_pickle(index_file)


def save_index(file_path, data):

    index_file = get_index_file(file_path)

    print("Index file:", index_file)

    if index_file is None:
        print("Index file is None")
        return

    dump_pickle_atomic(index_file, data)

    if index_file == "index.pkl":
        reload_document_cache()

    elif index_file == "image_index.pkl":
        reload_image_cache()

    elif index_file == "audio_index.pkl":
        reload_audio_cache()

    elif index_file == "video_index.pkl":
        reload_video_cache()

    print("Saved successfully")

def is_file_indexed(
    file_path,
    platform="local",
    file_id=None
):
    data = load_index(file_path)

    for item in data:

        if item.get("platform") != platform:
            continue

        if platform in ("google_drive", "github"):

           if item.get("file_id") == file_id:
               return True

        else:

            if item.get("path") == file_path:
                return True
    return False
    
def is_file_modified(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None
):

    import os

    data = load_index(file_path)

    if platform in ("github", "google_drive"):

        current_sha = file_sha

    else:

        current_modified = os.path.getmtime(file_path)

    for item in data:

        if item.get("platform") != platform:
            continue

        if platform in ("google_drive", "github"):

            if item.get("file_id") != file_id:
                continue

        else:

            if item.get("path") != file_path:
                continue

        if platform in ("github", "google_drive"):

            indexed_sha = item.get("sha")

            return current_sha != indexed_sha

        indexed_modified = item.get("last_modified", 0)

        return current_modified != indexed_modified 

    return True        

def remove_file_from_index(
    file_path,
    platform="local",
    file_id=None
):

    data = load_index(file_path)

    new_data = []

    for item in data:

        if item.get("platform") != platform:

            new_data.append(item)
            continue

        if platform in ("google_drive", "github"):

            if item.get("file_id") != file_id:
                new_data.append(item)

        else:

            if item.get("path") != file_path:
                new_data.append(item)

    save_index(
        file_path,
        new_data
    )

def remove_deleted_files():

    import os

    index_files = [
        "index.pkl",
        "image_index.pkl",
        "audio_index.pkl",
        "video_index.pkl"
    ]

    for index_file in index_files:

        if not os.path.exists(index_file):
            continue

        data = load_pickle(index_file)

        new_data = []

        for item in data:

            platform = item.get("platform", "local")

            # Google Drive handled later
            if platform in ("google_drive", "github"):
                new_data.append(item)
                continue

            path = item.get("path", "")

            print("Checking:", path)
            print("Exists:", os.path.exists(path))

            if os.path.exists(path):
                new_data.append(item)

        dump_pickle_atomic(index_file, new_data)

def remove_deleted_github_files():

    import pickle

    from app.platforms.github.github_service import (
        get_all_repository_paths
    )

    github_files = get_all_repository_paths()

    index_files = [
        "index.pkl",
        "image_index.pkl",
        "audio_index.pkl",
        "video_index.pkl"
    ]

    for index_file in index_files:

        if not os.path.exists(index_file):
            continue

        data = load_pickle(index_file)

        new_data = []

        for item in data:

            if item.get("platform") != "github":
                new_data.append(item)
                continue

            repo = item.get("repo")
            file_id = item.get("file_id")

            if (repo, file_id) in github_files:

                new_data.append(item)

            else:

                print(
                    f"Deleted from GitHub: {repo}/{file_id}"
                )

        dump_pickle_atomic(index_file, new_data)


    