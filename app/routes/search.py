from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.core.ownership import connected_platforms, owns_local_path, user_local_bases
from app.database.db import get_db
from app.models.request_models import SearchRequest
from app.services.search_service import search


router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


LOCAL_PLATFORMS = ("local", "local_storage")


def filter_owned_results(db: Session, user_id, results: list) -> list:
    """Keep only results this user owns.

    TODO(phase-3): stopgap until user_id is stored on every vector. The indexes
    are still global, so results are filtered after the search:
      - local: path inside one of the user's registered folders or upload dir
      - google_drive / github: kept only if the user has that platform connected
    """

    local_bases = user_local_bases(db, user_id)
    connected = connected_platforms(db, user_id)

    owned = []

    for result in results:

        platform = result.get("platform")

        if platform in LOCAL_PLATFORMS:
            if owns_local_path(local_bases, result.get("path")):
                owned.append(result)

        elif platform in connected:
            owned.append(result)

    return owned


@router.get("/health")
def health():

    return {
        "status": "Search API Ready"
    }


@router.post("/")
def search_files(
    request: SearchRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    results = search(
        query=request.query,
        platform=request.platform,
        search_type=request.search_type
    )

    results = filter_owned_results(
        db,
        current_user["id"],
        results
    )

    return {
        "query": request.query,
        "platform": request.platform,
        "search_type": request.search_type,
        "results": results
    }
