from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.models.request_models import SearchRequest
from app.services.search_service import search, suggestions
from app.models import response_models as rm


router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


@router.get("/health")
def health():

    return {
        "status": "Search API Ready"
    }


@router.get("/suggestions", response_model=rm.SuggestionsResponse)
def search_suggestions(
    prefix: str = Query("", max_length=200),
    current_user=Depends(get_current_user)
):
    """Autocomplete: up to 8 of the user's indexed file names."""

    return {"prefix": prefix, "suggestions": suggestions(current_user["id"], prefix)}


@router.post("/", response_model=rm.SearchResponse, response_model_exclude_unset=True)
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
        "results": found["results"],
        "possible_matches": found["possible_matches"]
    }
