from fastapi import APIRouter
from fastapi import Depends

from app.auth.auth_dependency import get_current_user
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
    current_user=Depends(get_current_user)
):

    # Isolation is enforced inside the vector queries (user_id must-filter),
    # replacing the Phase 1 post-filter.
    results = search(
        query=request.query,
        user_id=current_user["id"],
        platform=request.platform,
        search_type=request.search_type
    )

    return {
        "query": request.query,
        "platform": request.platform,
        "search_type": request.search_type,
        "results": results
    }
