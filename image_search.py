import re
import os
import sys
from rapidfuzz import fuzz
from clip_extract import get_text_embedding

from app.vectorstore.image_search import (  
    search_image_vectors,
)



# ==========================
# CONSTANTS
# ==========================

TOP_K = 5
MIN_FINAL_SCORE = 0.05

# ==========================
# HELPERS
# ==========================

def open_image(path):
    try:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        print(f"Could not open image: {e}")


def get_filename_score(query, filename):
    query = query.lower()

    # Improvement 4: normalise underscores and hyphens → spaces before tokenising
    filename = re.sub(r"[_\-]+", " ", filename.lower().rsplit(".", 1)[0])

    if query in filename:
        return 1.0

    query_words = set(re.findall(r"\w+", query))
    filename_words = set(re.findall(r"\w+", filename))

    if not query_words:
        return 0.0

    matches = len(query_words & filename_words)
    return matches / len(query_words)


def get_content_score(query, content):
    query = query.lower()
    content = content.lower()

    if query in content:
        return 1.0

    query_words = re.findall(r"\w+", query)
    content_words = set(re.findall(r"\w+", content))

    matches = 0
    for word in query_words:
        for c_word in content_words:
            if fuzz.ratio(word, c_word) >= 85:
                matches += 1
                break

    if not query_words:
        return 0.0

    return matches / len(query_words)


# ==========================
# SEARCH FUNCTION
# ==========================

def search_images(
    query,
    platform="all"
):
    if not query:
        return []

    query = query.strip().lower()

    query_embedding = get_text_embedding(query)

    images = search_image_vectors(
        query_embedding,
        limit=30,
        platform=platform
    )

    results = []

    for point in images:

        image = point.payload

        # Fix 2: pull CLIP score from lookup (0.0 if absent)
        clip_score = float(point.score)

        filename_score = get_filename_score(query, image.get("file", ""))
        content_score = get_content_score(query, image.get("ocr_text", ""))

        # Fix 3: adaptive ranking weights
        if content_score > 0:
            image_score = (
                0.50 * content_score +
                0.30 * filename_score +
                0.20 * clip_score
            )
        elif filename_score > 0:
            image_score = (
                0.60 * filename_score +
                0.40 * clip_score
            )
        else:
            image_score = clip_score

        # Fix 4: skip results below minimum threshold
        if image_score < MIN_FINAL_SCORE:
            continue

        results.append({
            "type": "image",
            "file": image.get("file", ""),
            "score": image_score,
            "path": image.get("path", ""),
            "platform": image.get("platform", "local"),
            "filename_score": filename_score,
            "ocr_score": content_score,
            "clip_score": clip_score,
            # Remove before production deployment (debug only)
            "ocr_text": image.get("ocr_text", ""),
            "file_id": image.get("file_id"),
        })

    # Fix 6: single sort at the end only
    results.sort(key=lambda x: x["score"], reverse=True)

    # Fix 9: use TOP_K constant
    return results[:TOP_K]


# ==========================
# MAIN SEARCH LOOP (terminal)
# ==========================

if __name__ == "__main__":

    while True:
        query = input("\nImage Query (exit): ").strip()

        if query.lower() == "exit":
            break

        results = search_images(query)

        if not results:
            print("\nNo relevant images found.")
            continue

        print("\nTop Image Results:\n")

        top_images = []

        for result in results:
            top_images.append({
                "file": result["file"],
                "path": result["path"],
            })

            print(result["file"])
            print(f"  Image Score : {result['score']:.4f}")
            print(f"  File Score  : {result['filename_score']:.4f}")   # Fix 7
            print(f"  OCR Score   : {result['ocr_score']:.4f}")
            print(f"  CLIP Score  : {result['clip_score']:.4f}")
            print()

        for i, img in enumerate(top_images, start=1):
            print(f"  {i}. {img['file']}")

        choice = input("\nEnter image number to open (0 to skip): ").strip()

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(top_images):
                open_image(top_images[idx - 1]["path"])