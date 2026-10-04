import re
import os
import time
import app.cache.search_cache as search_cache
from app.ai.model_manager import model_manager
from app.vectorstore.search import search_vectors
from embeddings import get_embeddings
from rapidfuzz import fuzz, process
from app.vectorstore.config import TEXT_COLLECTION


# ==========================
# CONFIGURATION
# ==========================

FUZZY_WORD_THRESHOLD = 85   # Min similarity score for a word match (0-100)
MIN_WORD_LENGTH      = 4    # Ignore words shorter than this (reduces noise)
SEMANTIC_THRESHOLD   = 0.35 # Min cosine similarity for semantic search

# ==========================
# LOAD MODEL & INDEX
# ==========================

print("Loading semantic model...")
model = model_manager.semantic_model
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
                and fuzz.ratio(q_word, c_word) >= 88
            ):
                found = True
                break

        if found:
            matches += 1

    return matches / len(query_words)


# Fix 1: all_documents is now an explicit parameter instead of a global
def get_file_fuzzy_score(
    filename,
    query_words
):

    best_score = 0

    chunks = search_cache.DOCUMENT_FILE_CHUNKS.get(
        filename,
        []
    )

    for doc in chunks:

        fuzzy_score = fuzzy_match_doc(
            doc,
            query_words
        )

        best_score = max(
            best_score,
            fuzzy_score
        )

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
# SEARCH FUNCTION
# ==========================

def search_documents(
    query,
    platform="all"
):

    if not query:
        return []

    all_documents = []

    print(f"Loaded {len(all_documents)} chunks from cache.")

    content_lookup = search_cache.DOCUMENT_CONTENT_LOOKUP
    
    query_words = [
        w for w in query.lower().split()
        if len(w) >= MIN_WORD_LENGTH
    ]

    # ----------------------------------
    # Semantic Scores
    # ----------------------------------

    t = time.perf_counter()

    t = time.perf_counter()

    query_embedding = get_embeddings([query])[0]

    print(
        f"Document Embedding: {time.perf_counter() - t:.3f} sec"
    )

    t = time.perf_counter()

    qdrant_results = search_vectors(
        query_embedding,
        TEXT_COLLECTION,
        limit=500,
        platform=platform
    )

    print(
        f"Qdrant Search: {time.perf_counter()-t:.3f} sec"
    )

    # Best semantic score per file
    semantic_lookup = {}

    for hit in qdrant_results:

        payload = hit.payload

        filename = payload["file"]

        score = float(hit.score)

        semantic_lookup[filename] = max(
            semantic_lookup.get(filename, 0),
            score
        )

    # ----------------------------------
    # Final Ranking
    # ----------------------------------

    final_results = {}
    unique_files = {}

    fuzzy_cache = {}

    for filename in search_cache.DOCUMENT_FILE_CHUNKS.keys():

        fuzzy_cache[filename] = get_file_fuzzy_score(
            filename,
            query_words
        )

    content_cache = {}

    for filename, content in content_lookup.items():

        content_cache[filename] = get_content_score(
            query,
            content
        )

    title_time = 0
    content_time = 0
    fuzzy_time = 0

    loop_start = time.perf_counter()

    for hit in qdrant_results:

        doc = hit.payload
        
        if (
            platform != "all"
            and doc.get("platform", "local") != platform
        ):
            continue

        filename = doc["file"]

        unique_key = (
            doc.get("platform"),
            doc.get("file_id") or doc.get("path") or filename
        )

        if unique_key in unique_files:
            continue

        unique_files[unique_key] = doc

        # ----------------------
        # Scores
        # ----------------------
        search_name = filename

        if doc.get("platform") == "github":
            search_name = doc.get("file_id", filename)

        t = time.perf_counter()

        title_score = get_title_score(
            query,
            search_name
        )

        title_time += time.perf_counter() - t
        
        t = time.perf_counter()

        content_score = content_cache.get(
            filename,
            0
        )
        
        content_time += time.perf_counter() - t

        # Fix 3: pass all_documents through to the helper
        t = time.perf_counter()

        fuzzy_score = fuzzy_cache.get(
            filename,
            0
        )

        fuzzy_time += time.perf_counter() - t

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

        final_results[unique_key] = (
            final_score,
            title_score,
            content_score,
            fuzzy_score,
            semantic_score,
            doc
        )
    
    print(
        f"Document Processing: {time.perf_counter()-loop_start:.3f} sec"
    )
    print(f"Title Score Time   : {title_time:.3f} sec")
    print(f"Content Score Time : {content_time:.3f} sec")
    print(f"Fuzzy Score Time   : {fuzzy_time:.3f} sec")
    
    sort_start = time.perf_counter()

    ranked = sorted(
        final_results.items(),
        key=lambda x: x[1][0],
        reverse=True
    )

    print(
        f"Sorting: {time.perf_counter()-sort_start:.3f} sec"
    )

    MIN_FINAL_SCORE = 0.30

    ranked = [
        item
        for item in ranked
        if item[1][0] >= MIN_FINAL_SCORE
    ]

    if not ranked:
        return []

    results = []

    for key, scores in ranked[:10]:
        (
            final_score,
            title_score,
            content_score,
            fuzzy_score,
            semantic_score,
            doc
        ) = scores

        results.append({
            "type": "document",
            "file": doc["file"],
            "repository_path": doc.get("file_id"),
            "score": final_score,
            "path": doc["path"],
            "platform": doc.get("platform", "local"),
            "title_score": title_score,
            "content_score": content_score,
            "fuzzy_score": fuzzy_score,
            "semantic_score": semantic_score,
            "file_id": doc.get("file_id"),
        })

    return results


# ==========================
# MAIN SEARCH LOOP (terminal)
# ==========================

if __name__ == "__main__":

    while True:

        query = input("\nEnter search query (or 'exit'): ").strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = search_documents(query)

        if not results:
            print("\nNo relevant documents found.")
            continue

        print("\n===================")
        print("Top Results")
        print("===================\n")

        top_docs = []

        for result in results:
            print(result["file"])
            print(f" Final Score    : {result['score']:.4f}")
            print(f" Title Score    : {result['title_score']:.4f}")
            print(f" Content Score  : {result['content_score']:.4f}")
            print(f" Fuzzy Score    : {result['fuzzy_score']:.4f}")
            print(f" Semantic Score : {result['semantic_score']:.4f}")
            print()

            top_docs.append({"file": result["file"], "path": result["path"]})

        prompt_pick_and_open(top_docs)