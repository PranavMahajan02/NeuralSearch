import os

from app.services.index_manager import (
    load_index,
    save_index
)

from video_extract import extract_video_text
from video_frame_extract import extract_frames
from clip_extract import get_image_embedding

from chunk import chunk_text
from embeddings import get_embeddings

from app.vectorstore.insert import insert_vectors
from app.vectorstore.delete import delete_vectors
from app.vectorstore.config import (
    VIDEO_COLLECTION,
    VIDEO_FRAME_COLLECTION,
)


def index_video(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    print(f"Indexing video: {file_path}")

    filename = os.path.basename(file_path)

    # ------------------------------------
    # Delete old vectors from Qdrant
    # ------------------------------------

    delete_vectors(
        collection_name=VIDEO_COLLECTION,
        platform=platform,
        file_id=file_id,
        path=file_path,
        repo=repo,
    )

    transcript = extract_video_text(file_path)

    print("Extracting frames...")

    frames = extract_frames(
        file_path,
        "temp_frames"
    )

    print(f"Frames Extracted: {len(frames)}")

    clip_embeddings = []
    new_frames = []

    for i, frame in enumerate(frames):

        try:

            embedding = get_image_embedding(frame)

            embedding = (
                embedding.tolist()
                if hasattr(embedding, "tolist")
                else embedding
            )

            clip_embeddings.append(embedding)

            new_frames.append(
                {
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
                    "frame_number": i,
                    "chunk": f"Frame {i}",
                    "embedding": embedding,
                }
            )

        except Exception as e:

            print(e)

    if transcript.strip():

        chunks = chunk_text(
            transcript,
            chunk_size=500
        )

        embeddings = get_embeddings(chunks)

    else:

        print("No transcript generated.")

        filename_text = (
            filename
            .rsplit(".", 1)[0]
            .replace("_", " ")
            .replace("-", " ")
        )

        chunks = [filename_text]

        embeddings = get_embeddings(chunks)

    all_video = load_index(file_path)

    new_videos = []

    for chunk, embedding in zip(chunks, embeddings):

        video = {
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
            ),
            "clip_embeddings": clip_embeddings
        }

        all_video.append(video)
        new_videos.append(video)

    save_index(
        file_path,
        all_video
    )

    # ------------------------------------
    # Store vectors in Qdrant
    # ------------------------------------
     
    insert_vectors(
        new_videos,
        VIDEO_COLLECTION
    )

    insert_vectors(
        new_frames,
        VIDEO_FRAME_COLLECTION
    )

    print("Video indexing completed.")