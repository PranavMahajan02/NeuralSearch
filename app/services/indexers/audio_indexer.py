import os

from app.services.index_manager import (
    load_index,
    save_index
)

from audio_extract import extract_audio_text
from chunk import chunk_text
from embeddings import get_embeddings


def index_audio(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    print(f"Indexing audio: {file_path}")

    filename = os.path.basename(file_path)

    transcript = extract_audio_text(file_path)

    if not transcript.strip():

        print("No transcript generated.")

        return

    print("Creating chunks...")

    chunks = chunk_text(
        transcript,
        chunk_size=500
    )

    print(f"Chunks Created: {len(chunks)}")

    print("Generating embeddings...")

    embeddings = get_embeddings(chunks)

    print("Embeddings Created")

    all_audio = load_index(file_path)

    for chunk, embedding in zip(chunks, embeddings):

        all_audio.append(
            {
                "file": filename,
                "path": file_path,
                "platform": platform,
                "file_id": file_id,
                "owner": owner,
                "repo": repo,
                "sha": file_sha,
                "last_modified": os.path.getmtime(file_path),
                "transcript": transcript,
                "chunk": chunk,
                "embedding": embedding
            }
        )

    save_index(
        file_path,
        all_audio
    )

    print("Audio indexing completed.")