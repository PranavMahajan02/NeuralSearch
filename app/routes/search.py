from fastapi import APIRouter

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
def search_files(request: SearchRequest):

    results = search(
    request.query,
    request.platform
    )

    return {
    "query": request.query,
    "platform": request.platform,
    "results": results
}