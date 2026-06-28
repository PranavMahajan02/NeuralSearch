from video_search import search_video

def search_video_file(
    query: str,
    platform="all"
):
    return search_video(
        query,
        platform
    )