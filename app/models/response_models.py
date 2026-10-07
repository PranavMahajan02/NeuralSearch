"""Response models of the JSON API.

They document every response in /openapi.json, from which the frontend's
TypeScript types are generated (frontend: `npm run gen:api`).
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


# ---- search ------------------------------------------------------------------

class MatchInfo(BaseModel):
    reasons: List[str]
    field: str
    snippet: str
    # [start, end) character offsets into `snippet` of the matched terms.
    highlights: List[List[int]]


class SearchResult(BaseModel):
    platform: str
    source_id: str
    type: str
    file: str
    display_path: str
    path: str
    score: float
    match: MatchInfo
    file_size: Optional[int] = None
    modified_at: Optional[str] = None
    mime_type: Optional[str] = None
    extension: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    debug: Optional[Dict[str, Optional[float]]] = None


class SearchResponse(BaseModel):
    query: str
    platform: str
    search_type: str
    limit: int
    offset: int
    total: int
    results: List[SearchResult]


class Suggestion(BaseModel):
    file: str
    platform: str
    type: str


class SuggestionsResponse(BaseModel):
    prefix: str
    suggestions: List[Suggestion]


# ---- dashboard ---------------------------------------------------------------

class RecentFile(BaseModel):
    platform: str
    source_id: str
    file: str
    display_path: str
    type: str
    indexed_at: Optional[str] = None


class RecentResponse(BaseModel):
    files: List[RecentFile]


class PlatformDetail(BaseModel):
    connected: bool
    indexed_files: int
    last_indexed_at: Optional[str] = None
    folders: Optional[List[str]] = None


class DashboardStats(BaseModel):
    total_files: int
    documents: int
    images: int
    audio: int
    video: int
    by_platform: Dict[str, int]
    no_content_files: int
    failed_files: int
    last_indexed_at: Optional[datetime] = None
    connected_platforms: int
    supported_platforms: int
    ready_platforms: int
    platforms: Dict[str, PlatformDetail]


# ---- indexing jobs -------------------------------------------------------------

JobStatus = Literal["queued", "running", "completed", "completed_with_errors", "failed", "cancelled"]


class Job(BaseModel):
    id: str
    platform: str
    status: JobStatus
    total_files: int
    processed_files: int
    succeeded_files: int
    failed_files: int
    skipped_files: int
    downloaded_files: int
    indexed_files: int
    progress: int
    current_file: str
    error_message: Optional[str] = None
    cancel_requested: bool
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None


class JobWithHistory(Job):
    indexed: bool
    history: Optional[List[Job]] = None


class JobError(BaseModel):
    file: str
    error: str
    created_at: Optional[datetime] = None


class JobErrorsResponse(BaseModel):
    job_id: str
    failed_files: int
    errors: List[JobError]


class IndexQueuedResponse(BaseModel):
    status: str
    message: str
    priority_platform: str
    platforms: List[str]
    jobs: List[Job]


# ---- platforms -------------------------------------------------------------------

class FoldersResponse(BaseModel):
    folders: List[str]
    # The native folder dialog exists only when the backend runs in development.
    picker_available: bool
    status: Optional[str] = None
    purged_files: Optional[int] = None


class PickFolderResponse(BaseModel):
    folder: str


class DriveStatus(BaseModel):
    connected: bool
    account_email: Optional[str] = None


class GithubStatus(BaseModel):
    connected: bool
    account_name: Optional[str] = None


class ConnectResponse(BaseModel):
    status: str
    connected: bool
    authorization_url: Optional[str] = None
    account_email: Optional[str] = None
    username: Optional[str] = None
    message: Optional[str] = None


class DisconnectResponse(BaseModel):
    status: str
    connected: bool
    revoked: Optional[bool] = None
    purged_files: int
    message: str


class OpenResponse(BaseModel):
    type: Literal["url", "download"]
    url: str
    filename: Optional[str] = None


class LoginStateResponse(BaseModel):
    has_indexed: bool
    platforms: List[str]
