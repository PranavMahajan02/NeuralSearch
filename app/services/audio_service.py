from audio_search import search_audio

def search_audio_file(
    query: str,
    platform="all"
):
    return search_audio(
        query,
        platform
    )