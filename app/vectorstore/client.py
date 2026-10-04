from qdrant_client import QdrantClient

from app.core.config import settings

client = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT
)

print("Connected to Qdrant!")