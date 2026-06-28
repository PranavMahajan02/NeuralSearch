import os

from app.services.index_delete import remove_from_index

UPLOAD_FOLDER = "data"


def delete_file(filename):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    if not os.path.exists(file_path):

        return {
            "status": "error",
            "message": "File not found."
        }

    print(f"Deleting: {filename}")

    os.remove(file_path)

    remove_from_index(
        "index.pkl",
        filename
    )

    remove_from_index(
        "image_index.pkl",
        filename
    )

    remove_from_index(
        "audio_index.pkl",
        filename
    )

    remove_from_index(
        "video_index.pkl",
        filename
    )

    print(f"Deleted: {filename}")

    return {
        "status": "success",
        "message": "File deleted successfully."
    }