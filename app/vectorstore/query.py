"""The only read path into Qdrant for search.

Every query is built here with a mandatory must-filter on user_id, so no
caller can forget it: a missing user_id raises instead of searching everyone.
"""


from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.vectorstore.client import get_client
from app.vectorstore.config import collection_for_type

ALL_PLATFORMS = (None, "", "all")


class MissingUserScope(ValueError):
    """A vector query without a user_id: refused (would search every user)."""


def user_filter(user_id: str, platform: str | None = None, **extra) -> Filter:

    if not user_id:
        raise MissingUserScope("Vector queries must be scoped to a user_id.")

    must = [FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))]

    if platform not in ALL_PLATFORMS:
        must.append(FieldCondition(key="platform", match=MatchValue(value=platform)))

    for key, value in extra.items():
        must.append(FieldCondition(key=key, match=MatchValue(value=value)))

    return Filter(must=must)


def search_points(
    point_type: str,
    vector: list[float],
    user_id: str,
    platform: str | None = None,
    limit: int = 100
):
    """Nearest neighbours of `vector` among this user's points of one type."""

    result = get_client().query_points(
        collection_name=collection_for_type(point_type),
        query=list(vector),
        query_filter=user_filter(user_id, platform),
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    return result.points
