import re

from app.ai.model_manager import model_manager

from app.vectorstore.audio_search import (
    search_audio_vectors,
)


# ==========================
# CONFIG
# ==========================

TOP_K = 5
MIN_SCORE = 0.15

# ==========================
# LOAD MODEL
# ==========================

print(
    "Loading semantic model..."
)

model = model_manager.semantic_model

print("Ready.\n")

# ==========================
# HELPER FUNCTIONS
# ==========================

def get_filename_score(
    query,
    filename
):

    query = query.lower()

    filename = (
        filename.lower()
        .rsplit(".", 1)[0]
    )

    if query == filename:
        return 1.0

    if query in filename:
        return 0.9

    query_words = set(
        re.findall(
            r"\w+",
            query
        )
    )

    filename_words = set(
        re.findall(
            r"\w+",
            filename
        )
    )

    if not query_words:
        return 0

    matches = len(
        query_words &
        filename_words
    )

    return matches / len(
        query_words
    )


def get_content_score(
    query,
    transcript
):

    query = query.lower()

    transcript = (
        transcript.lower()
    )

    if query in transcript:
        return 1.0

    query_words = set(
        re.findall(
            r"\w+",
            query
        )
    )

    transcript_words = set(
        re.findall(
            r"\w+",
            transcript
        )
    )

    if not query_words:
        return 0

    matches = len(
        query_words &
        transcript_words
    )

    return matches / len(
        query_words
    )


# ==========================
# SEARCH FUNCTION
# ==========================

def search_audio(
    query,
    platform="all"
):

    if not query:
        return []

    query = query.strip().lower()

    # ----------------------
    # Query Embedding
    # ----------------------

    query_embedding = model.encode(query).tolist()

    audios = search_audio_vectors(
        query_embedding,
        limit=100,
        platform=platform,
    )

    # ----------------------
    # Search
    # ----------------------

    results = []

    for point in audios:

        audio = point.payload

        if (
            platform != "all"
            and audio.get("platform", "local") != platform
        ):
            continue

        semantic_score = float(point.score)

        filename_score = (
            get_filename_score(
                query,
                audio.get("file", "")
            )
        )

        content_score = (
            get_content_score(
                query,
                audio.get("chunk", "")
            )
        )

        final_score = (
            0.20 * filename_score +
            0.40 * content_score +
            0.40 * semantic_score
        )

        results.append(
            (
                float(final_score),
                float(filename_score),
                float(content_score),
                float(semantic_score),
                audio
            )
        )

    # ----------------------
    # Sort Results
    # ----------------------

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # ----------------------
    # Remove Duplicates
    # ----------------------

    unique_results = []

    seen_files = set()

    for (
        final_score,
        filename_score,
        content_score,
        semantic_score,
        audio
    ) in results:

        if final_score < MIN_SCORE:
            continue

        filename = audio.get("file", "")

        if filename in seen_files:
            continue

        seen_files.add(
            filename
        )

        unique_results.append(
            (
                final_score,
                filename_score,
                content_score,
                semantic_score,
                audio
            )
        )

    # ----------------------
    # No Results
    # ----------------------

    if not unique_results:
        return []

    # ----------------------
    # Build Output
    # ----------------------

    output = []

    for (
        final_score,
        filename_score,
        content_score,
        semantic_score,
        audio
    ) in unique_results[:TOP_K]:

        output.append({
            "type": "audio",
            "file": audio.get("file", ""),
            "score": final_score,
            "path": audio["path"],
            "platform": audio.get("platform", "local"),
            "filename_score": filename_score,
            "content_score": content_score,
            "semantic_score": semantic_score,
            "preview": audio.get("chunk", "")[:300],
            "file_id": audio.get("file_id"),
        })

    return output


# ==========================
# MAIN SEARCH LOOP (terminal)
# ==========================

if __name__ == "__main__":

    while True:

        query = input(
            "\nAudio Query (exit): "
        ).strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = search_audio(query)

        if not results:

            print(
                "\nNo relevant audio found."
            )

            continue

        print(
            "\n===================="
        )

        print(
            "TOP AUDIO RESULTS"
        )

        print(
            "====================\n"
        )

        for result in results:

            print(
                f"File : {result['file']}"
            )

            print(
                f"Final Score    : {result['score']:.4f}"
            )

            print(
                f"Filename Score : {result['filename_score']:.4f}"
            )

            print(
                f"Content Score  : {result['content_score']:.4f}"
            )

            print(
                f"Semantic Score : {result['semantic_score']:.4f}"
            )

            print(
                "\nChunk Preview::"
            )

            print(
                result["preview"]
            )

            print(
                "\n------------------------\n"
            )