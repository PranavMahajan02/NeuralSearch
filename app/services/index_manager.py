import os
import pickle

DOCUMENTS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv",

    ".py",
    ".java",
    ".js",
    ".ts",
    ".tsx",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".sql",
    ".sh"
)

IMAGES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif"
)

AUDIOS = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac"
)

VIDEOS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
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

    if not os.path.exists(index_file):
        return []

    with open(index_file, "rb") as f:
        return pickle.load(f)


def save_index(file_path, data):

    index_file = get_index_file(file_path)

    print("Index file:", index_file)

    if index_file is None:
        print("Index file is None")
        return

    with open(index_file, "wb") as f:
        pickle.dump(data, f)

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

    if platform == "github":

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

        if platform == "github":

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

        with open(index_file, "rb") as f:
            data = pickle.load(f)

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

        with open(index_file, "wb") as f:
            pickle.dump(new_data, f)

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

        with open(index_file, "rb") as f:
            data = pickle.load(f)

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

        with open(index_file, "wb") as f:

            pickle.dump(
                new_data,
                f
            )


    

    

    