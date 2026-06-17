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

content_lookup = {}

for doc in all_documents:
    filename = doc["file"]
    
    if filename not in content_lookup:
        content_lookup[filename] = ""
        
    content_lookup[filename] += " " + doc["chunk"]
    if filename == "final report.docx":
        if "ADT24SOCB0787" in doc["chunk"]:
            print("\nFOUND IN CHUNK")
            print(doc["chunk"][:300])

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


def get_title_score(query, filename):

    query = query.lower()
    filename = filename.lower()
    filename = filename.rsplit(".", 1)[0]

    if query == filename:
        return 1.0

    if query in filename:
        return 0.9

    query_words = set(
        re.findall(r"\w+", query)
    )

    filename_words = set(
        re.findall(r"\w+", filename)
    )

    if not query_words:
        return 0

    matches = len(
        query_words &
        filename_words
    )

    return matches / len(query_words)


def get_content_score(query, content):

    # Exact phrase match
    if query.lower() in content.lower():
        return 1.0

    query_words = set(
        re.findall(r"\w+", query.lower())
    )

    content_words = set(
        re.findall(r"\w+", content.lower())
    )

    if not query_words:
        return 0.0

    matches = 0

    for q_word in query_words:

        # Exact word match
        if q_word in content_words:
            matches += 1
            continue

        # Fuzzy fallback
        found = False

        for c_word in content_words:
            
            if (
    abs(len(q_word) - len(c_word)) <= 2
    and
    fuzz.ratio(q_word, c_word) >= 88
):
                found = True
                break

        if found:
            matches += 1

    return matches / len(query_words)


def get_file_fuzzy_score(filename, query_words):
    best_score = 0

    for doc in all_documents:
        if doc["file"] != filename:
            continue

        fuzzy_score = fuzzy_match_doc(doc, query_words)
        best_score = max(best_score, fuzzy_score)
        
    return best_score / 100


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
        break

    if not query:
        continue

    query_words = [
        w for w in query.lower().split()
        if len(w) >= MIN_WORD_LENGTH
    ]

    # ----------------------------------
    # Semantic Scores
    # ----------------------------------

    query_embedding = model.encode([query])
    
    semantic_scores = cosine_similarity(
        query_embedding,
        [doc["embedding"] for doc in all_documents]
    )[0]

    # Best semantic score per file
    semantic_lookup = {}

    for doc, score in zip(all_documents, semantic_scores):
        filename = doc["file"]

        if filename not in semantic_lookup:
            semantic_lookup[filename] = float(score)
        else:
            semantic_lookup[filename] = max(
                semantic_lookup[filename],
                float(score)
            )

    # ----------------------------------
    # Final Ranking
    # ----------------------------------

    final_results = {}
    unique_files = {}

    for doc in all_documents:
        filename = doc["file"]

        if filename in unique_files:
            continue

        unique_files[filename] = doc

        # ----------------------
        # Scores
        # ----------------------
        title_score = get_title_score(query, filename)
        
        content_score = get_content_score(
            query,
            content_lookup.get(filename, "")
        )

        fuzzy_score = get_file_fuzzy_score(filename, query_words)

        semantic_score = semantic_lookup.get(filename, 0)
        
        if semantic_score < SEMANTIC_THRESHOLD:
            semantic_score = 0

        # ----------------------
        # Final Score
        # ----------------------
        final_score = (
            0.40 * title_score +
            0.25 * content_score +
            0.10 * fuzzy_score +
            0.25 * semantic_score
        )

        final_results[filename] = (
            final_score,
            title_score,
            content_score,
            fuzzy_score,
            semantic_score,
            doc
        )

    ranked = sorted(
        final_results.items(),
        key=lambda x: x[1][0],
        reverse=True
    )
    
    MIN_FINAL_SCORE = 0.30

    ranked = [
        item
        for item in ranked
        if item[1][0] >= MIN_FINAL_SCORE
    ]

    if not ranked:
        print("\nNo relevant documents found.")
        continue

    print("\n===================")
    print("Top Results")
    print("===================\n")

    top_docs = []

    for file, scores in ranked[:10]:
        (
            final_score,
            title_score,
            content_score,
            fuzzy_score,
            semantic_score,
            doc
        ) = scores

        print(file)
        print(f" Final Score    : {final_score:.4f}")
        print(f" Title Score    : {title_score:.4f}")
        print(f" Content Score  : {content_score:.4f}")
        print(f" Fuzzy Score    : {fuzzy_score:.4f}")
        print(f" Semantic Score : {semantic_score:.4f}")
        print()

        top_docs.append(doc)

    prompt_pick_and_open(top_docs)