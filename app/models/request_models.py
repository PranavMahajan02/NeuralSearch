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
    path: Optional[str] = None
    file_id: Optional[str] = None
    # Preferred: the result's source_id (local path / Drive id / owner/repo:path).
    source_id: Optional[str] = None