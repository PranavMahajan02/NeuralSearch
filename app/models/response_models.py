"""Response models of the JSON API.

They document every response in /openapi.json, from which the frontend's
TypeScript types are generated (frontend: `npm run gen:api`).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

# ---- search ------------------------------------------------------------------

class MatchInfo(BaseModel):
    reasons: list[str]
    field: str
    snippet: str
    # [start, end) character offsets into `snippet` of the matched terms.
    highlights: list[list[int]]
    # Videos matched on what a frame shows: that frame's time in seconds.
    frame_time_s: int | None = None
    # "low" for possible_matches (below the visual evidence threshold).
    confidence: str | None = None


class SearchResult(BaseModel):
    platform: str
    source_id: str
    type: str
    file: str
    display_path: str
    path: str
    score: float
    match: MatchInfo
    file_size: int | None = None
    modified_at: str | None = None
    mime_type: str | None = None
    extension: str | None = None
    owner: str | None = None
    repo: str | None = None
    debug: dict[str, float | None] | None = None


class SearchResponse(BaseModel):
    query: str
    platform: str
    search_type: str
    limit: int
    offset: int
    total: int
    results: list[SearchResult]
    # Low-confidence visual matches: never in results, never counted in total.
    possible_matches: list[SearchResult] = []


class Suggestion(BaseModel):
    file: str
    platform: str
    type: str


class SuggestionsResponse(BaseModel):
    prefix: str
    suggestions: list[Suggestion]


# ---- dashboard ---------------------------------------------------------------

class RecentFile(BaseModel):
    platform: str
    source_id: str
    file: str
    display_path: str
    type: str
    indexed_at: str | None = None


class RecentResponse(BaseModel):
    files: list[RecentFile]


class PlatformDetail(BaseModel):
    connected: bool
    indexed_files: int
    last_indexed_at: str | None = None
    folders: list[str] | None = None


class DashboardStats(BaseModel):
    total_files: int
    documents: int
    images: int
    audio: int
    video: int
    by_platform: dict[str, int]
    no_content_files: int
    failed_files: int
    last_indexed_at: datetime | None = None
    connected_platforms: int
    supported_platforms: int
    ready_platforms: int
    platforms: dict[str, PlatformDetail]


# ---- indexing jobs -------------------------------------------------------------

JobStatus = Literal["queued", "running", "completed", "completed_with_errors", "failed", "cancelled"]


class Job(BaseModel):
    id: str
    platform: str
    status: JobStatus
    priority: int = 0
    total_files: int
    processed_files: int
    succeeded_files: int
    failed_files: int
    skipped_files: int
    downloaded_files: int
    indexed_files: int
    progress: int
    current_file: str
    error_message: str | None = None
    cancel_requested: bool
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    # Where the time went: seconds per stage, calls, and per file type.
    stage_timings: dict[str, Any] | None = None


class JobWithHistory(Job):
    indexed: bool
    history: list[Job] | None = None


class JobError(BaseModel):
    file: str
    error: str
    created_at: datetime | None = None


class JobErrorsResponse(BaseModel):
    job_id: str
    failed_files: int
    errors: list[JobError]


class IndexQueuedResponse(BaseModel):
    status: str
    message: str
    priority_platform: str
    platforms: list[str]
    jobs: list[Job]


# ---- platforms -------------------------------------------------------------------

class FoldersResponse(BaseModel):
    folders: list[str]
    # The native folder dialog exists only when the backend runs in development.
    picker_available: bool
    status: str | None = None
    purged_files: int | None = None


class PickFolderResponse(BaseModel):
    folder: str


class DriveStatus(BaseModel):
    connected: bool
    account_email: str | None = None


class GithubStatus(BaseModel):
    connected: bool
    account_name: str | None = None


class ConnectResponse(BaseModel):
    status: str
    connected: bool
    authorization_url: str | None = None
    account_email: str | None = None
    username: str | None = None
    message: str | None = None


class DisconnectResponse(BaseModel):
    status: str
    connected: bool
    revoked: bool | None = None
    purged_files: int
    message: str


class OpenResponse(BaseModel):
    type: Literal["url", "download"]
    url: str
    filename: str | None = None


class LoginStateResponse(BaseModel):
    has_indexed: bool
    platforms: list[str]
