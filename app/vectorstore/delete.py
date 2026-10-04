from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)

from app.vectorstore.client import client


def delete_vectors(
    collection_name,
    platform="local",
    file_id=None,
    path=None,
    repo=None,
):
    conditions = [
        FieldCondition(
            key="platform",
            match=MatchValue(value=platform),
        )
    ]

    if platform == "local":

        conditions.append(
            FieldCondition(
                key="path",
                match=MatchValue(value=path),
            )
        )

    elif platform == "google_drive":

        conditions.append(
            FieldCondition(
                key="file_id",
                match=MatchValue(value=file_id),
            )
        )

    elif platform == "github":

        conditions.append(
            FieldCondition(
                key="repo",
                match=MatchValue(value=repo),
            )
        )

        conditions.append(
            FieldCondition(
                key="file_id",
                match=MatchValue(value=file_id),
            )
        )

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=conditions
        ),
        wait=True,
    )

    print("Old vectors removed.")