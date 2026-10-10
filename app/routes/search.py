from fastapi import APIRouter, Depends, Query, Request

from app.auth.auth_dependency import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.core.metrics import SEARCH_LATENCY
from app.core.rate_limit import limiter, user_key
from app.models import response_models as rm
from app.models.request_models import SearchRequest
from app.services.search_service import search, suggestions

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/health")
def health():

    return {"status": "Search API Ready"}


@router.get("/suggestions", response_model=rm.SuggestionsResponse)
def search_suggestions(prefix: str = Query("", max_length=200), current_user=Depends(get_current_user)):
    """Autocomplete: up to 8 of the user's indexed file names."""

    return {"prefix": prefix, "suggestions": suggestions(current_user["id"], prefix)}


@router.post("/", response_model=rm.SearchResponse, response_model_exclude_unset=True)
@limiter.limit(settings.SEARCH_RATE_LIMIT, key_func=user_key)
def search_files(
    request: Request,
    body: SearchRequest,
    debug: bool = Query(False, description="Include score components (development only)."),
    current_user=Depends(get_current_user),
):

    if debug and settings.is_production:
        raise AppError(400, "debug is only available in development.")

    # Isolation is enforced inside the queries (user_id filter), not after.
    with SEARCH_LATENCY.time():
        found = search(
            query=body.query,
            user_id=current_user["id"],
            platform=body.platform.value,
            search_type=body.search_type.value,
            limit=body.limit,
            offset=body.offset,
            debug=debug,
        )

    return {
        "query": body.query,
        "platform": body.platform.value,
        "search_type": body.search_type.value,
        "limit": body.limit,
        "offset": body.offset,
        "total": found["total"],
        "results": found["results"],
        "possible_matches": found["possible_matches"],
    }
