import pickle
import os
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process

# ==========================
# CONFIGURATION
# ==========================

FUZZY_WORD_THRESHOLD = 85   # Min similarity score for a word match (0-100)
MIN_WORD_LENGTH      = 4    # Ignore words shorter than this (reduces noise)
SEMANTIC_THRESHOLD   = 0.35 # Min cosine similarity for semantic search
INDEX_FILE           = "index.pkl"

# ==========================
# LOAD MODEL & INDEX
# ==========================

print("Loading index...")

with open(INDEX_FILE, "rb") as f:
    all_documents = pickle.load(f)

print(f"Loaded {len(all_documents)} chunks")

print("Loading semantic model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Ready.\n")


# ==========================
# HELPER FUNCTIONS
# ==========================

def open_file(path: str) -> None:
    """Cross-platform file open."""
    try:
        if os.name == "nt":               # Windows
            os.startfile(path)
        elif os.uname().sysname == "Darwin":  # macOS
            os.system(f'open "{path}"')
        else:                                 # Linux
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        print(f"Could not open file: {e}")


def prompt_open(path: str) -> None:
    """Ask the user whether to open a file."""
    choice = input("\nOpen file? (y/n): ").strip().lower()
    if choice == "y":
        open_file(path)


def prompt_pick_and_open(unique_docs: list) -> None:
    """Show a numbered list and let the user pick one to open."""
    for i, doc in enumerate(unique_docs, start=1):
        print(f"  {i}. {doc['file']}")

    choice = input("\nEnter file number to open (0 to skip): ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(unique_docs):
            open_file(unique_docs[idx - 1]["path"])


def fuzzy_match_doc(doc: dict, query_words: list) -> int:
    """
    Return the best fuzzy match score (0-100) between any query word
    and any word in the document chunk.

    Three-layer false-positive filter:
      1. Strip punctuation from chunk words so "operuting," == "operuting".
      2. Length guard: chunk word must be within ±40% length of the query
         word, so a 3-char chunk word can never score 80+ against a 9-char
         query word just by character-overlap luck.
      3. fuzz.ratio (whole-string) instead of partial_ratio, so the scorer
         compares the full word, not the best lucky substring.
    """
    # Strip leading/trailing punctuation from every chunk word
    chunk_words = [
        re.sub(r"^\W+|\W+$", "", w)
        for w in doc["chunk"].lower().split()
    ]

    # Drop empty strings and words shorter than MIN_WORD_LENGTH
    chunk_words = [w for w in chunk_words if len(w) >= MIN_WORD_LENGTH]

    if not chunk_words:
        return 0

    best = 0
    for q_word in query_words:
        q_len = len(q_word)

        # Length guard: only consider chunk words whose length is within
        # 30% of the query word length, floor of 1 for short words.
        # e.g. "pranav"(6) → ±1 → candidates 5-7 chars only.
        #      "operating"(9) → ±2 → candidates 7-11 chars only.
        # Tighter than the old ±40% to stop short common words
        # fuzzy-matching names and producing false positives.
        length_tolerance = max(1, int(q_len * 0.3))
        candidates = [
            w for w in chunk_words
            if abs(len(w) - q_len) <= length_tolerance
        ]

        if not candidates:
            continue

        result = process.extractOne(
            q_word,
            candidates,
            scorer=fuzz.ratio,
            score_cutoff=FUZZY_WORD_THRESHOLD,
        )
        if result is not None:
            best = max(best, result[1])

    return best


# ==========================
# MAIN SEARCH LOOP
# ==========================

while True:

    query = input("\nEnter search query (or 'exit'): ").strip()

    if query.lower() == "exit":
        print("Goodbye.")
        break

    if not query:
        continue

    query_lower = query.lower()

    # ----------------------------------------
    # 1. FILE NAME SEARCH
    #    Exact substring match against file name (no extension).
    # ----------------------------------------

    file_found = False

    for doc in all_documents:
        filename_without_ext = os.path.splitext(doc["file"])[0].lower()

        if query_lower in filename_without_ext:
            print("\n===================")
            print("Matched by file name:")
            print(f"  {doc['file']}")
            print("===================")

            prompt_open(doc["path"])
            file_found = True
            break

    if file_found:
        continue

    # ----------------------------------------
    # 2. FUZZY SEARCH
    # ----------------------------------------

    # Build query word list
    query_words = [
        w for w in query_lower.split()
        if len(w) >= MIN_WORD_LENGTH
    ]

    if not query_words:
        query_words = query_lower.split()

    matched_docs = []

    for doc in all_documents:

        score = fuzzy_match_doc(
            doc,
            query_words
        )

        if score >= FUZZY_WORD_THRESHOLD:
            matched_docs.append(
                (score, doc)
            )

    if matched_docs:
        matched_docs.sort(
            key=lambda x: x[0],
            reverse=True
        )

        unique_docs = []
        seen = set()

        for score, doc in matched_docs:
            if doc["file"] not in seen:
                unique_docs.append(doc)
                seen.add(doc["file"])

        print("\n===================")
        print(f"Search match — {len(unique_docs)} file(s) found:")
        print("===================")

        prompt_pick_and_open(unique_docs)

        continue

    # ----------------------------------------
    # 3. SEMANTIC SEARCH
    #    Falls through only when fuzzy search finds nothing.
    #    Uses cosine similarity on sentence embeddings.
    # ----------------------------------------

    print("\nNo fuzzy match found. Trying semantic search...")

    query_embedding = model.encode([query])

    scores = cosine_similarity(
        query_embedding,
        [doc["embedding"] for doc in all_documents]
    )[0]

    best_index = int(scores.argmax())
    best_score = float(scores[best_index])

    if best_score < SEMANTIC_THRESHOLD:
        print("\nNo relevant document found.")
        continue

    doc = all_documents[best_index]

    print("\n===================")
    print("Best semantic match:")
    print(f"  File  : {doc['file']}")
    print(f"  Score : {best_score:.3f}")
    print(f"  Chunk : {doc['chunk'][:300]}{'...' if len(doc['chunk']) > 300 else ''}")
    print("===================")

    prompt_open(doc["path"])