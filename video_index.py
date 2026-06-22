import os
import pickle

from video_extract import (
    extract_video_text
)

from chunk import (
    chunk_text
)

from embeddings import (
    get_embeddings
)

from video_frame_extract import (
    extract_frames
)

from clip_extract import (
    get_image_embedding
)

SUPPORTED_VIDEO = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
)


def build_video_index(
    data_folder="data"
):

    all_video = []

    print(
        "\n=========================="
    )

    print(
        "VIDEO INDEXING STARTED"
    )

    print(
        "==========================\n"
    )

    for filename in os.listdir(
        data_folder
    ):

        if not filename.lower().endswith(
            SUPPORTED_VIDEO
        ):
            continue

        file_path = os.path.join(
            data_folder,
            filename
        )

        print(
            f"\nProcessing: {filename}"
        )

        transcript = (
            extract_video_text(
                file_path
            )
        )
        
        # ----------------------
        # FRAME EXTRACTION
        # ----------------------

        print("Extracting frames...")

        frames = extract_frames(
            file_path,
            "temp_frames"
        )

        print(
            f"Frames Extracted: {len(frames)}"
        )

        # ----------------------
        # CLIP EMBEDDINGS
        # ----------------------

        clip_embeddings = []

        for frame in frames:

            try:

                embedding = (
                    get_image_embedding(
                        frame
                    )
                )

                clip_embeddings.append(
                    embedding
                )

            except Exception as e:

                print(
                    f"Frame Error: {e}"
                )

        # ----------------------
        # TRANSCRIPT CHUNKING
        # ----------------------

        if not transcript.strip():

            print(
                "No transcript generated."
            )

            continue

        chunks = chunk_text(
            transcript,
            chunk_size=500
        )

        embeddings = (
            get_embeddings(
                chunks
            )
        )

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):

            all_video.append(
                {
                    "file": filename,
                    "path": file_path,
                    "transcript": transcript,
                    "chunk": chunk,
                    "embedding": embedding,
                    "clip_embeddings": clip_embeddings
                }
            )

    # ----------------------
    # SAVE INDEX
    # ----------------------

    with open(
        "video_index.pkl",
        "wb"
    ) as f:

        pickle.dump(
            all_video,
            f
        )

    print(
        f"\nVideo Files Indexed: "
        f"{len(set([v['file'] for v in all_video]))}"
    )

    print(
        f"Total Video Chunks: "
        f"{len(all_video)}"
    )

    print(
        "\nvideo_index.pkl saved."
    )


if __name__ == "__main__":

    build_video_index()