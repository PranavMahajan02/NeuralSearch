from app.vectorstore.client import client
from app.vectorstore.config import IMAGE_COLLECTION

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)


def search_image_vectors(
    embedding,
    limit=20,
    platform="all"
):

    query_filter = None

    if platform != "all":

        query_filter = Filter(

            must=[

                FieldCondition(
                    key="platform",
                    match=MatchValue(value=platform)
                )

            ]

        )

    result = client.query_points(

        collection_name=IMAGE_COLLECTION,

        query=embedding,

        limit=limit,

        query_filter=query_filter

    )

    return result.points