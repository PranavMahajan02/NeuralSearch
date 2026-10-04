from document_search_v2 import (
    search_documents
)

from image_search import (
    search_images
)

from audio_search import (
    search_audio
)

from video_search import (
    search_video
)


def unified_search(query):

    if not query:
        return []

    results = []

    # -------------------
    # Documents
    # -------------------

    try:

        results.extend(
            search_documents(query)
        )

    except Exception as e:

        print(
            f"Document Search Error: {e}"
        )

    # -------------------
    # Images
    # -------------------

    try:

        results.extend(
            search_images(query)
        )

    except Exception as e:

        print(
            f"Image Search Error: {e}"
        )

    # -------------------
    # Audio
    # -------------------

    try:

        results.extend(
            search_audio(query)
        )

    except Exception as e:

        print(
            f"Audio Search Error: {e}"
        )

    # -------------------
    # Video
    # -------------------

    try:

        results.extend(
            search_video(query)
        )

    except Exception as e:

        print(
            f"Video Search Error: {e}"
        )

    # -------------------
    # Sort Results
    # -------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results


if __name__ == "__main__":

    while True:

        query = input(
            "\nUnified Query (exit): "
        ).strip()

        if query.lower() == "exit":
            break

        results = unified_search(
            query
        )

        if not results:

            print(
                "\nNo results found."
            )

            continue

        print(
            "\n===================="
        )

        print(
            "UNIFIED RESULTS"
        )

        print(
            "====================\n"
        )

        for result in results[:10]:

            print(
                f"[{result['type'].upper()}]"
            )

            print(
                result["file"]
            )

            print(
                f"Score: {result['score']:.4f}"
            )

            print(
                f"Platform: {result.get('platform', 'local')}"
            )

            print(
                "\n------------------------\n"
            )