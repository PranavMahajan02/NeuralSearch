"""Collections, payload indexes and deterministic point IDs."""

import uuid

from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from app.vectorstore.client import get_client
from app.vectorstore.config import COLLECTION_SPECS, INDEXED_PAYLOAD_FIELDS, collection_name

# Fixed namespace: the same (user, platform, source, type, chunk) always maps
# to the same point id, so re-indexing overwrites instead of duplicating.
POINT_NAMESPACE = uuid.UUID("6f1d3c2a-8b4e-5f60-9a7b-c3d2e1f0a9b8")


def point_id(
    user_id: str, platform: str, source_id: str, point_type: str, chunk_index: int, frame_number: int | None = None
) -> str:

    key = f"{user_id}|{platform}|{source_id}|{point_type}|{chunk_index}|{'' if frame_number is None else frame_number}"

    return str(uuid.uuid5(POINT_NAMESPACE, key))


def ensure_collections() -> list:
    """Create missing collections and payload indexes (idempotent).
    Returns the names of collections that were created."""

    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    created = []

    for key, size in COLLECTION_SPECS.items():
        name = collection_name(key)

        if name not in existing:
            client.create_collection(
                collection_name=name, vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )
            created.append(name)

        schema = client.get_collection(name).payload_schema or {}

        for field in INDEXED_PAYLOAD_FIELDS:
            if field not in schema:
                client.create_payload_index(
                    collection_name=name, field_name=field, field_schema=PayloadSchemaType.KEYWORD, wait=True
                )

        if "chunk_index" not in schema:
            client.create_payload_index(
                collection_name=name, field_name="chunk_index", field_schema=PayloadSchemaType.INTEGER, wait=True
            )

    return created
