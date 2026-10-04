from app.vectorstore.client import client
from app.vectorstore.config import VIDEO_COLLECTION

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)


def search_video_vectors(
    embedding,
    limit=100,
    platform="all",
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

        collection_name=VIDEO_COLLECTION,

        query=embedding,

        limit=limit,

        query_filter=query_filter

    )

    return result.points