from app.services.searchers.document_searcher import search_document
from app.services.searchers.image_searcher import search_image
from app.services.searchers.audio_searcher import search_audio
from app.services.searchers.video_searcher import search_video


def search_file(query):

    results = []

    results.extend(
        search_document(query)
    )

    results.extend(
        search_image(query)
    )

    results.extend(
        search_audio(query)
    )

    results.extend(
        search_video(query)
    )

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results