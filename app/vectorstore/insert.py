from uuid import uuid4

from qdrant_client.models import PointStruct

from app.vectorstore.client import client



def insert_vectors(
    documents,
    collection_name
):

    points = []

    for document in documents:

        payload = {
            "file": document["file"],
            "path": document["path"],
            "platform": document["platform"],
            "file_id": document["file_id"],
            "owner": document["owner"],
            "repo": document["repo"],
            "sha": document["sha"],
            "last_modified": document["last_modified"],
            "chunk": document["chunk"],
            "ocr_text": document.get("ocr_text"),
        }

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=document["embedding"],
                payload=payload
            )
        )

    if points:

        client.upsert(
            collection_name=collection_name,
            points=points
        )

        print(
            f"Inserted {len(points)} vectors into {collection_name}."
        )