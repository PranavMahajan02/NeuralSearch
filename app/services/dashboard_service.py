import os
import pickle
from app.scheduler.status import get_status

def count_index(index_file):

    if not os.path.exists(index_file):
        return 0

    with open(index_file, "rb") as f:
        data = pickle.load(f)

    files = set()

    for item in data:

        files.add(
            (
                item.get("platform"),
                item.get("file")
            )
        )

    return len(files)

def get_dashboard_stats():

    documents = count_index("index.pkl")

    images = count_index("image_index.pkl")

    audio = count_index("audio_index.pkl")

    video = count_index("video_index.pkl")

    total = (
        documents
        + images
        + audio
        + video
    )

    scheduler = get_status()

    return {

        "total_files": total,

        "documents": documents,

        "images": images,

        "audio": audio,

        "video": video,

        "connected_platforms": len(
            scheduler["completed_platforms"]
        ),

        "ready_platforms": len(
            scheduler["completed_platforms"]
        )
    }