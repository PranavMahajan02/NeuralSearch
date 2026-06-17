import pickle
import re

from rapidfuzz import fuzz

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


print("Loading index...")

with open("index.pkl", "rb") as f:
    all_documents = pickle.load(f)

content_lookup = {}

for doc in all_documents:

    filename = doc["file"]

    if filename not in content_lookup:
        content_lookup[filename] = ""

    content_lookup[filename] += (
        " " + doc["chunk"]
    )

print("Loading MiniLM...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Ready.")


def get_filename_score(
    query,
    filename
):

    query = query.lower()

    filename = filename.lower()

    filename = filename.rsplit(
        ".",
        1
    )[0]

    if query == filename:
        return 1.0

    if query in filename:
        return 0.9

    return fuzz.ratio(
        query,
        filename
    ) / 100


def get_content_score(
    query,
    content
):

    query = query.lower()

    content = content.lower()

    if query in content:
        return 1.0

    query_words = re.findall(
        r"\w+",
        query
    )

    content_words = set(
        re.findall(
            r"\w+",
            content
        )
    )

    matches = 0

    for word in query_words:

        if word in content_words:
            matches += 1

    if not query_words:
        return 0

    return matches / len(
        query_words
    )


while True:

    query = input(
        "\nDocument Query (exit): "
    ).strip()

    if query.lower() == "exit":
        break

    query_embedding = model.encode(
        [query]
    )

    similarities = cosine_similarity(
        query_embedding,
        [
            doc["embedding"]
            for doc in all_documents
        ]
    )[0]

    file_scores = {}

    for doc, score in zip(
        all_documents,
        similarities
    ):

        file_scores[
            doc["file"]
        ] = max(
            file_scores.get(
                doc["file"],
                0
            ),
            float(score)
        )

    results = []

    for file in file_scores:

        filename_score = (
            get_filename_score(
                query,
                file
            )
        )

        content_score = (
            get_content_score(
                query,
                content_lookup.get(
                    file,
                    ""
                )
            )
        )

        semantic_score = (
            file_scores[file]
        )

        final_score = (
            0.45 * filename_score
            +
            0.35 * content_score
            +
            0.20 * semantic_score
        )

        results.append(
            (
                final_score,
                file,
                filename_score,
                content_score,
                semantic_score
            )
        )

    results.sort(
        reverse=True
    )

    print("\nTop Results:\n")

    for result in results[:5]:

        (
            final_score,
            file,
            filename_score,
            content_score,
            semantic_score
        ) = result

        print(file)

        print(
            f" Final Score : {final_score:.4f}"
        )

        print(
            f" Filename    : {filename_score:.4f}"
        )

        print(
            f" Content     : {content_score:.4f}"
        )

        print(
            f" Semantic    : {semantic_score:.4f}"
        )

        print()