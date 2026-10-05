"""Collection layout of the v2 index (one collection per vector space)."""

from app.core.config import settings


# point "type" -> (collection suffix, vector size)
#   text / audio / video transcripts: all-MiniLM-L6-v2 (384)
#   images / video frames: CLIP ViT-B/32 (512)
COLLECTION_SPECS = {
    "text": 384,
    "image": 512,
    "audio": 384,
    "video": 384,
    "video_frames": 512,
}

TYPE_TO_COLLECTION = {
    "document": "text",
    "image": "image",
    "audio": "audio",
    "video": "video",
    "video_frame": "video_frames",
}

POINT_TYPES = tuple(TYPE_TO_COLLECTION)

# Keyword payload indexes: every query filters on these.
INDEXED_PAYLOAD_FIELDS = ("user_id", "platform", "source_id", "type")


def collection_name(key: str) -> str:
    """'text' -> 'cogniseek_v2_text' (prefix from settings)."""

    if key not in COLLECTION_SPECS:
        raise ValueError(f"Unknown collection '{key}'.")

    return f"{settings.QDRANT_COLLECTION_PREFIX}_{key}"


def collection_for_type(point_type: str) -> str:

    return collection_name(TYPE_TO_COLLECTION[point_type])


def all_collections():

    return [collection_name(key) for key in COLLECTION_SPECS]
