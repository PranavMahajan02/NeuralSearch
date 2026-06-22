import os
import pickle

from audio_extract import (
    extract_audio_text
)

from chunk import (
    chunk_text
)

from embeddings import (
    get_embeddings
)

SUPPORTED_AUDIO = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac"
)


def build_audio_index(
    data_folder="data"
):

    all_audio = []

    print(
        "\n=========================="
    )
    print(
        "AUDIO INDEXING STARTED"
    )
    print(
        "==========================\n"
    )

    for filename in os.listdir(
        data_folder
    ):

        if not filename.lower().endswith(
            SUPPORTED_AUDIO
        ):
            continue

        file_path = os.path.join(
            data_folder,
            filename
        )

        print(
            f"\nProcessing: {filename}"
        )

        # ----------------------
        # TRANSCRIPTION
        # ----------------------

        transcript = (
            extract_audio_text(
                file_path
            )
        )

        if not transcript.strip():

            print(
                "No transcript generated."
            )

            continue

        print(
            f"Transcript Length: "
            f"{len(transcript)} chars"
        )

        # ----------------------
        # CHUNKING
        # ----------------------

        chunks = chunk_text(
            transcript,
            chunk_size=500
        )

        print(
            f"Chunks Created: "
            f"{len(chunks)}"
        )

        # ----------------------
        # EMBEDDINGS
        # ----------------------

        embeddings = (
            get_embeddings(
                chunks
            )
        )

        # ----------------------
        # STORE
        # ----------------------

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):

            all_audio.append(
                {
                    "file": filename,
                    "path": file_path,
                    "transcript": transcript,
                    "chunk": chunk,
                    "embedding": embedding
                }
            )

    # ----------------------
    # SAVE
    # ----------------------

    with open(
        "audio_index.pkl",
        "wb"
    ) as f:

        pickle.dump(
            all_audio,
            f
        )

    print(
        "\n=========================="
    )

    print(
        f"Audio Files Indexed: "
        f"{len(set([a['file'] for a in all_audio]))}"
    )

    print(
        f"Total Audio Chunks: "
        f"{len(all_audio)}"
    )

    print(
        "\naudio_index.pkl saved."
    )


if __name__ == "__main__":

    build_audio_index()