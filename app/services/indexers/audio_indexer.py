import os

from app.services.index_manager import (
    load_index,
    save_index
)

from audio_extract import extract_audio_text
from chunk import chunk_text
from embeddings import get_embeddings
from app.vectorstore.insert import insert_vectors
from app.vectorstore.delete import delete_vectors
from app.vectorstore.config import AUDIO_COLLECTION

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

    delete_vectors(
        collection_name=AUDIO_COLLECTION,
        platform=platform,
        file_id=file_id,
        path=file_path,
        repo=repo,
    )

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

    new_audio = []

    all_audio = load_index(file_path)

    for chunk, embedding in zip(chunks, embeddings):

        audio = {
            "file": filename,
            "path": file_path,
            "platform": platform,
            "file_id": file_id,
            "owner": owner,
            "repo": repo,
            "sha": file_sha,
            "last_modified": (
                file_sha
                if platform == "google_drive"
                else os.path.getmtime(file_path)
            ),
            "transcript": transcript,
            "chunk": chunk,
            "embedding": (
                embedding.tolist()
                if hasattr(embedding, "tolist")
                else embedding
            )
        }

        all_audio.append(audio)
        new_audio.append(audio)

    save_index(
        file_path,
        all_audio
    )

    insert_vectors(
        new_audio,
        AUDIO_COLLECTION
    )

    print("Audio indexing completed.")