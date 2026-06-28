import os

DOCUMENTS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv"
)

IMAGES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif"
)

AUDIOS = (
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac"
)

VIDEOS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv"
)


def index_file(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension in DOCUMENTS:

        from app.services.indexers.document_indexer import index_document

        index_document(
        file_path,
        platform=platform,
        file_id=file_id,
        file_sha=file_sha,
        owner=owner,
        repo=repo
        )

    elif extension in IMAGES:

        from app.services.indexers.image_indexer import index_image

        index_image(
        file_path,
        platform=platform,
        file_id=file_id,
        file_sha=file_sha,
        owner=owner,
        repo=repo
        )

    elif extension in AUDIOS:

        from app.services.indexers.audio_indexer import index_audio

        index_audio(
        file_path,
        platform=platform,
        file_id=file_id,
        file_sha=file_sha,
        owner=owner,
        repo=repo
        )

    elif extension in VIDEOS:

        from app.services.indexers.video_indexer import index_video

        index_video(
        file_path,
        platform=platform,
        file_id=file_id,
        file_sha=file_sha,
        owner=owner,
        repo=repo
        )

    else:

        print(
            f"Unsupported file type: {extension}"
        )