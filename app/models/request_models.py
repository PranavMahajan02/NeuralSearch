from pydantic import BaseModel
from typing import Optional


class SearchRequest(BaseModel):
    query: str
    platform: str = "all"
    search_type: str = "all"


class FolderRequest(BaseModel):
    folder: str


class OpenRequest(BaseModel):
    platform: str
    path: str
    file_id: Optional[str] = None