import pickle
import os

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading Index...")

with open("index.pkl", "rb") as f:
    all_documents = pickle.load(f)

print(f"Loaded {len(all_documents)} chunks")

while True:

    query = input("\nEnter Search Query (or type exit): ")

    if query.lower() == "exit":
        break

    query_lower = query.lower()

    # ==========================
    # FILE NAME SEARCH
    # ==========================

    file_found = False

    for doc in all_documents:

        filename_without_ext = os.path.splitext(
            doc["file"]
        )[0].lower()

        if query_lower in filename_without_ext:

            print("\n===================")
            print("Matched File:")
            print(doc["file"])
            print("===================")

            choice = input(
                "\nOpen file? (y/n): "
            )

            if choice.lower() == "y":
                os.startfile(doc["path"])

            file_found = True
            break

    if file_found:
        continue

    # ==========================
    # FUZZY SEARCH
    # ==========================

    matched_docs = []

    for doc in all_documents:

        score = fuzz.token_set_ratio(
            query_lower,
            doc["chunk"].lower()
        )

        if score > 90:

            if doc not in matched_docs:
                matched_docs.append(doc)

    if matched_docs:

        print("\n===================")
        print("Found In:")
        print("===================")

        unique_docs = []

        seen = set()

        for doc in matched_docs:

            if doc["file"] not in seen:

                unique_docs.append(doc)
                seen.add(doc["file"])

        for i, doc in enumerate(
            unique_docs,
            start=1
        ):
            print(f"{i}. {doc['file']}")

        choice = input(
            "\nEnter file number to open (0 to skip): "
        )

        if choice.isdigit():

            choice = int(choice)

            if 1 <= choice <= len(unique_docs):

                os.startfile(
                    unique_docs[
                        choice - 1
                    ]["path"]
                )

        continue

    # ==========================
    # SEMANTIC SEARCH
    # ==========================

    query_embedding = model.encode([query])

    scores = cosine_similarity(
        query_embedding,
        [doc["embedding"]
         for doc in all_documents]
    )[0]

    best_index = scores.argmax()

    best_score = scores[best_index]

    if best_score < 0.35:

        print(
            "\nNo relevant document found."
        )

        continue

    doc = all_documents[best_index]

    print("\n===================")
    print("Best Match:")
    print(doc["file"])
    print("\nScore:")
    print(best_score)
    print("\nContent:")
    print(doc["chunk"])
    print("===================")

    choice = input(
        "\nOpen file? (y/n): "
    )

    if choice.lower() == "y":
        os.startfile(doc["path"])