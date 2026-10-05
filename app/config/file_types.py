DOCUMENTS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".md",
    ".markdown",
    ".csv",

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

# Plain-text document formats (read as text, no parser).
TEXT_DOCUMENTS = tuple(
    ext for ext in DOCUMENTS if ext not in (".pdf", ".docx", ".pptx", ".csv")
)


def file_type_for(name: str):
    """'document' | 'image' | 'audio' | 'video' | None (unsupported)."""

    import os

    extension = os.path.splitext(name or "")[1].lower()

    if extension in DOCUMENTS:
        return "document"
    if extension in IMAGES:
        return "image"
    if extension in AUDIOS:
        return "audio"
    if extension in VIDEOS:
        return "video"

    return None
