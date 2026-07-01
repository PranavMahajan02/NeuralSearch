import os

DOCUMENTS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv",

    # Source Code
    ".py",
    ".java",
    ".js",
    ".ts",
    ".tsx",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".sql",
    ".sh"
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

    print("\n==========================")
    print("INDEX FILE :", file_path)
    print("EXTENSION  :", extension)
    print("==========================")

    if extension in DOCUMENTS:

        print("DOCUMENT")

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

        print("IMAGE")

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

        print("AUDIO")

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

        print("VIDEO")

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

        print(f"Unsupported file type: {extension}")