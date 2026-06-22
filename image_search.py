import pickle
import re
import os
import sys
from rapidfuzz import fuzz

from clip_utils import clip_search


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


with open(
    "image_index.pkl",
    "rb"
) as f:
    image_index = pickle.load(f)


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

        found = False

        for c_word in content_words:

            if fuzz.ratio(word, c_word) >= 85:

                found = True
                break

        if found:
            matches += 1

    if not query_words:
        return 0

    return matches / len(
        query_words
    )


# ==========================
# SEARCH FUNCTION
# ==========================

def search_images(query):

    if not query:
        return []

    clip_results = clip_search(
        query
    )

    MIN_IMAGE_SCORE = 0.20

    filtered_results = []

    for clip_score, image in clip_results:

        if clip_score >= MIN_IMAGE_SCORE:

            filtered_results.append(
                (clip_score, image)
            )

    filtered_results = sorted(
        filtered_results,
        key=lambda x: x[0],
        reverse=True
    )

    if not filtered_results:
        return []

    results = []

    for clip_score, image in filtered_results[:5]:

        content_score = (
            get_content_score(
                query,
                image.get(
                    "ocr_text",
                    ""
                )
            )
        )

        if content_score > 0:
            image_score = (
                0.90 * content_score
                +
                0.10 * clip_score
            )
        else:
            image_score = clip_score

        results.append({
            "type": "image",
            "file": image["file"],
            "score": image_score,
            "path": image["path"],
            "platform": image.get("platform", "local"),
            "ocr_score": content_score,
            "clip_score": float(clip_score)
        })

    return results


# ==========================
# MAIN SEARCH LOOP (terminal)
# ==========================

if __name__ == "__main__":

    while True:

        query = input(
            "\nImage Query (exit): "
        ).strip()

        if query.lower() == "exit":
            break

        results = search_images(query)

        if not results:

            print(
                "\nNo relevant images found."
            )

            continue

        print(
            "\nTop Image Results:\n"
        )

        top_images = []

        # 1. Process and print the results
        for result in results:

            top_images.append({
                "file": result["file"],
                "path": result["path"]
            })

            print(
                result["file"]
            )

            print(
                f"  Image Score : {result['score']:.4f}"
            )

            print(
                f"  OCR Score   : {result['ocr_score']:.4f}"
            )

            print(
                f"  CLIP Score  : {result['clip_score']:.4f}"
            )

            print()

        # 2. Show the numbered list to the user
        for i, img in enumerate(top_images, start=1):
            print(f"  {i}. {img['file']}")

        # 3. Prompt to open the image
        choice = input(
            "\nEnter image number to open (0 to skip): "
        ).strip()

        if choice.isdigit():

            idx = int(choice)

            if 1 <= idx <= len(top_images):

                open_image(
                    top_images[idx - 1]["path"]
                )