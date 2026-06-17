import pickle
import re

from rapidfuzz import fuzz

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from clip_utils import clip_search


print("Loading text index...")

with open("index.pkl", "rb") as f:
    all_documents = pickle.load(f)

print(f"Loaded {len(all_documents)} chunks")


print("Loading image index...")

with open("image_index.pkl", "rb") as f:
    image_index = pickle.load(f)


content_lookup = {}

for doc in all_documents:

    filename = doc["file"]

    if filename not in content_lookup:
        content_lookup[filename] = ""

    content_lookup[filename] += " " + doc["chunk"]


print("Loading MiniLM...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Ready.")


# ======================================
# CONTENT SCORING
# ======================================

def get_filename_score(query, filename):

    query = query.lower().strip()
    filename = filename.lower()

    filename = filename.rsplit(".", 1)[0]

    if query == filename:
        return 1.0

    if query in filename:
        return 0.9

    query_words = query.split()

    filename_words = re.findall(
        r"\w+",
        filename
    )

    matches = 0

    for q in query_words:

        for f in filename_words:

            if fuzz.ratio(q, f) >= 85:
                matches += 1
                break

    if query_words:
        return matches / len(query_words)

    return 0.0


def get_content_score(query, content):

    query = query.lower()
    content = content.lower()

    # Exact content match
    if query in content:
        return 1.0

    query_words = re.findall(
        r"\w+",
        query
    )

    content_words = re.findall(
        r"\w+",
        content
    )

    if not query_words:
        return 0.0

    matches = 0

    for query_word in query_words:

        best_score = 0

        for content_word in content_words:

            score = fuzz.ratio(
                query_word,
                content_word
            )

            best_score = max(
                best_score,
                score
            )

        if best_score >= 85:
            matches += 1

    return matches / len(query_words)


# ======================================
# SEARCH LOOP
# ======================================

while True:

    query = input(
        "\nEnter search query (or 'exit'): "
    ).strip()

    if query.lower() == "exit":
        break

    # ----------------------------------
    # SEMANTIC SEARCH (MiniLM)
    # ----------------------------------

    query_embedding = model.encode(
        [query]
    )

    text_scores = cosine_similarity(
        query_embedding,
        [doc["embedding"] for doc in all_documents]
    )[0]

    file_scores = {}

    for doc, score in zip(
        all_documents,
        text_scores
    ):

        filename = doc["file"]

        if filename not in file_scores:

            file_scores[filename] = float(score)

        else:

            file_scores[filename] = max(
                file_scores[filename],
                float(score)
            )

    # ----------------------------------
    # CLIP SEARCH
    # ----------------------------------

    clip_results = clip_search(query)

    clip_scores = {}

    for score, image in clip_results:

        clip_scores[
            image["file"]
        ] = float(score)

    # ----------------------------------
    # COMBINE
    # ----------------------------------

    FILENAME_WEIGHT = 0.45
    CONTENT_WEIGHT = 0.35  # Updated from OCR_WEIGHT
    SEMANTIC_WEIGHT = 0.15
    CLIP_WEIGHT = 0.05

    final_scores = {}

    all_files = set(
        list(file_scores.keys())
        +
        list(clip_scores.keys())
    )

    for file in all_files:

        filename_score = get_filename_score(
            query,
            file
        )

        semantic_score = file_scores.get(
            file,
            0
        )

        clip_score = clip_scores.get(
            file,
            0
        )

        content_text = content_lookup.get(
            file,
            ""
        )

        content_score = get_content_score(
            query,
            content_text
        )

        final_score = (
            FILENAME_WEIGHT * filename_score
            +
            CONTENT_WEIGHT * content_score
            +
            SEMANTIC_WEIGHT * semantic_score
            +
            CLIP_WEIGHT * clip_score
        )

        final_scores[file] = (
            final_score,
            filename_score,
            semantic_score,
            clip_score,
            content_score
        )

    ranked = sorted(
        final_scores.items(),
        key=lambda x: x[1][0],
        reverse=True
    )
    
    print("\nTop Results:\n")

    for file, scores in ranked[:5]:

        (
            final_score,
            filename_score,
            semantic_score,
            clip_score,
            content_score
        ) = scores

        print(file)

        print(
            f"  Final Score    : {final_score:.4f}"
        )

        print(
            f"  Filename Score : {filename_score:.4f}"
        )

        print(
            f"  Semantic Score : {semantic_score:.4f}"
        )

        print(
            f"  CLIP Score     : {clip_score:.4f}"
        )

        print(
            f"  Content Score  : {content_score:.4f}"
        )

        print()