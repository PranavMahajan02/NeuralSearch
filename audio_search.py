import pickle
import re

from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

# ==========================
# CONFIG
# ==========================

TOP_K = 5
MIN_SCORE = 0.15

# ==========================
# LOAD INDEX
# ==========================

print("Loading audio index...")

with open(
    "audio_index.pkl",
    "rb"
) as f:

    all_audio = pickle.load(f)

print(
    f"Loaded {len(all_audio)} audio chunks"
)

# ==========================
# LOAD MODEL
# ==========================

print(
    "Loading semantic model..."
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

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
# SEARCH LOOP
# ==========================

while True:

    query = input(
        "\nAudio Query (exit): "
    ).strip()

    if query.lower() == "exit":
        break

    if not query:
        continue

    # ----------------------
    # Query Embedding
    # ----------------------

    query_embedding = model.encode(
        [query]
    )

    # ----------------------
    # Search
    # ----------------------

    results = []

    for audio in all_audio:

        semantic_score = cosine_similarity(
            query_embedding,
            [audio["embedding"]]
        )[0][0]

        filename_score = (
            get_filename_score(
                query,
                audio["file"]
            )
        )

        content_score = (
            get_content_score(
                query,
                audio["transcript"]
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

        filename = audio["file"]

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

        print(
            "\nNo relevant audio found."
        )

        continue

    # ----------------------
    # Display Results
    # ----------------------

    print(
        "\n===================="
    )

    print(
        "TOP AUDIO RESULTS"
    )

    print(
        "====================\n"
    )

    for (
        final_score,
        filename_score,
        content_score,
        semantic_score,
        audio
    ) in unique_results[:TOP_K]:

        print(
            f"File : {audio['file']}"
        )

        print(
            f"Final Score    : {final_score:.4f}"
        )

        print(
            f"Filename Score : {filename_score:.4f}"
        )

        print(
            f"Content Score  : {content_score:.4f}"
        )

        print(
            f"Semantic Score : {semantic_score:.4f}"
        )

        print(
            "\nTranscript Preview:"
        )

        print(
            audio["chunk"][:300]
        )

        print(
            "\n------------------------\n"
        )