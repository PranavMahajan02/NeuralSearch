import os
import re
import torch
from app.ai.model_manager import model_manager
from app.vectorstore.video_search import (
    search_video_vectors,
)

from app.vectorstore.video_frame_search import (
    search_video_frame_vectors,
)

TOP_K = 5
MIN_SCORE = 0.05  # Reduced from 0.10 (matches image search threshold)

model = model_manager.semantic_model
print("Loading CLIP...")

clip_model = model_manager.clip_model
clip_processor = model_manager.clip_processor

print("CLIP Ready")


def get_filename_score(
    query,
    filename
):
    # Normalize: lowercase, strip extension, replace _ and - with spaces
    filename = re.sub(
        r"[_\-]+",
        " ",
        filename.lower().rsplit(".", 1)[0]
    )

    # query already normalized by caller
    if query == filename:
        return 1.0

    if query in filename:
        return 0.95  # Raised from 0.9

    query_words = set(
        re.findall(
            r"\w+",
            query
        )
    )

    # After normalization, \w+ tokenization works correctly
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
    # query already normalized by caller
    transcript = str(transcript).lower()

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

def search_video(
    query,
    platform="all"
):

    if not query:
        return []

    query_embedding = model.encode(query).tolist()

    videos = search_video_vectors(
        query_embedding,
        limit=100,
        platform=platform,
    )

    clip_inputs = clip_processor(
        text=[query],
        return_tensors="pt",
        padding=True
    )

    clip_inputs = {
        k: v.to(model_manager.device)
        for k, v in clip_inputs.items()
    }

    with torch.no_grad():

        query_clip_embedding = (
            clip_model
            .get_text_features(
                **clip_inputs
            )
            .cpu()
        .numpy()[0]
    )

    frame_points = search_video_frame_vectors(
        query_clip_embedding.tolist(),
        limit=1000,
        platform=platform,
    )

    clip_scores = {}

    for point in frame_points:

        payload = point.payload

        filename = payload["file"]

        clip_scores[filename] = max(
            clip_scores.get(filename, 0),
            float(point.score)
        )

    results = []

    for point in videos:

        video = point.payload
        if (
            platform != "all"
            and video.get("platform", "local") != platform
        ):
            continue

        if "file" not in video:
            continue

        embedding = video.get("embedding")

        if embedding is None:
            semantic_score = 0.0
        else:
            semantic_score = float(point.score)

        best_clip_score = clip_scores.get(
            video["file"],
            0.0
        )

        filename_score = (
            get_filename_score(
                query,
                video["file"]
            )
        )

        content_score = (
            get_content_score(
                query,
                video.get("transcript", "")  # Safe access
            )
        )

        # Adaptive scoring: weight shifts based on which signals fire
        if filename_score > 0:

            final_score = (
                0.50 * filename_score +
                0.20 * content_score +
                0.15 * semantic_score +
                0.15 * best_clip_score
            )

        elif content_score > 0:

            final_score = (
                0.60 * content_score +
                0.25 * semantic_score +
                0.15 * best_clip_score
            )

        else:

            final_score = (
                0.60 * semantic_score +
                0.40 * best_clip_score
            )

        results.append(
            (
                final_score,
                filename_score,
                content_score,
                semantic_score,
                best_clip_score,
                video
            )
        )

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # ----------------------
    # Remove Duplicates
    # ----------------------

    unique_results = []

    shown = set()

    for (
        final_score,
        filename_score,
        content_score,
        semantic_score,
        best_clip_score,
        video
    ) in results:

        if final_score < MIN_SCORE:
            continue

        filename = video.get("file", "")

        if filename in shown:
            continue

        shown.add(filename)

        unique_results.append(
            (
                final_score,
                filename_score,
                content_score,
                semantic_score,
                best_clip_score,
                video
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
        best_clip_score,
        video
    ) in unique_results[:TOP_K]:

        output.append({
    "type": "video",
    "file": video.get("file", ""),
    "score": float(final_score),
    "path": video.get("path", ""),
    "platform": video.get("platform", "local"),
    "filename_score": float(filename_score),
    "content_score": float(content_score),
    "semantic_score": float(semantic_score),
    "clip_score": float(best_clip_score),
    "preview": video.get("chunk", "")[:300],
    "file_id": video.get("file_id"),
})

    return output


# ==========================
# MAIN SEARCH LOOP (terminal)
# ==========================

if __name__ == "__main__":

    while True:

        query = input(
            "\nVideo Query (exit): "
        ).strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = search_video(query)

        print(
            "\n===================="
        )

        print(
            "TOP VIDEO RESULTS"
        )

        print(
            "====================\n"
        )

        if not results:

            print(
                "\nNo relevant videos found."
            )

            continue

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
                f"CLIP Score     : {result['clip_score']:.4f}"
            )

            print(
                "\nTranscript Preview:"
            )

            print(
                result["preview"]
            )

            print(
                "\n------------------------\n"
            )