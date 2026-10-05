from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.models.request_models import SearchRequest
from app.services.search_service import search


router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


@router.get("/health")
def health():

    return {
        "status": "Search API Ready"
    }


@router.post("/")
def search_files(
    request: SearchRequest,
    debug: bool = Query(False, description="Include score components (development only)."),
    current_user=Depends(get_current_user)
):

    if debug and settings.is_production:
        raise AppError(400, "debug is only available in development.")

    # Isolation is enforced inside the queries (user_id filter), not after.
    found = search(
        query=request.query,
        user_id=current_user["id"],
        platform=request.platform.value,
        search_type=request.search_type.value,
        limit=request.limit,
        offset=request.offset,
        debug=debug
    )

    return {
        "query": request.query,
        "platform": request.platform.value,
        "search_type": request.search_type.value,
        "limit": request.limit,
        "offset": request.offset,
        "total": found["total"],
        "results": found["results"]
    }
