from pydantic import BaseModel
from typing import List


class SearchResult(BaseModel):
    file: str
    score: float
    type: str


class SearchResponse(BaseModel):
    results: List[SearchResult]