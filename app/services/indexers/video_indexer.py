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

    transcript = extract_video_text(file_path)

    print("Extracting frames...")

    frames = extract_frames(
        file_path,
        "temp_frames"
    )

    print(f"Frames Extracted: {len(frames)}")

    clip_embeddings = []

    for frame in frames:

        try:

            embedding = get_image_embedding(frame)

            clip_embeddings.append(embedding)

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

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        all_video.append(
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
                "embedding": embedding,
                "clip_embeddings": clip_embeddings
            }
        )

    save_index(
        file_path,
        all_video
    )

    print("Video indexing completed.")