import os

from app.services.index_manager import (
    load_index,
    save_index
)

from clip_extract import get_image_embedding
from paddle_extract import extract_text as paddle_ocr

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import IMAGE_COLLECTION
from app.vectorstore.delete import delete_vectors


def index_image(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    print(f"Indexing image: {file_path}")

    filename = os.path.basename(file_path)

    delete_vectors(
        collection_name=IMAGE_COLLECTION,
        platform=platform,
        file_id=file_id,
        path=file_path,
        repo=repo,
    )

    embedding = get_image_embedding(file_path)

    ocr_text = paddle_ocr(file_path)

    all_images = load_index(file_path)

    all_images.append(
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
            "embedding": embedding,
            "ocr_text": ocr_text
        }
    )

    save_index(
        file_path,
        all_images
    )

    # -----------------------------
    # Store image embedding in Qdrant
    # -----------------------------
    new_images = [
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
            "chunk": ocr_text,
            "ocr_text": ocr_text,
            "embedding": embedding
        }
    ]

    insert_vectors(
        new_images,
        IMAGE_COLLECTION
    )

    print("Image indexing completed.")