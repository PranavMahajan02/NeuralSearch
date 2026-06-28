import json
import os

CONFIG_FILE = "app/config/local_storage.json"


def load_local_folders():

    if not os.path.exists(CONFIG_FILE):
        return []

    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)

    return data.get("folders", [])


def save_local_folders(folders):

    with open(CONFIG_FILE, "w") as f:
        json.dump(
            {
                "folders": folders
            },
            f,
            indent=4
        )


def add_folder(folder):

    folders = load_local_folders()

    if folder not in folders:
        folders.append(folder)

    save_local_folders(folders)


def remove_folder(folder):

    folders = load_local_folders()

    if folder in folders:
        folders.remove(folder)

    save_local_folders(folders)