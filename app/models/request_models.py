from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SearchPlatform(str, Enum):

    all = "all"
    local = "local"
    google_drive = "google_drive"
    github = "github"


class SearchType(str, Enum):

    all = "all"
    document = "document"
    image = "image"
    audio = "audio"
    video = "video"


PLATFORM_ALIASES = {"local_storage": "local"}

MAX_QUERY_LENGTH = 500


class SearchRequest(BaseModel):

    query: str
    platform: SearchPlatform = SearchPlatform.all
    search_type: SearchType = SearchType.all
    limit: int = Field(20, ge=1, le=50)
    offset: int = Field(0, ge=0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError("Query must not be empty.")

        if len(value) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query must be at most {MAX_QUERY_LENGTH} characters.")

        return value

    @field_validator("platform", mode="before")
    @classmethod
    def platform_alias(cls, value):

        if isinstance(value, str):
            value = value.strip().lower()
            return PLATFORM_ALIASES.get(value, value)

        return value

    @field_validator("search_type", mode="before")
    @classmethod
    def search_type_case(cls, value):

        return value.strip().lower() if isinstance(value, str) else value


class FolderRequest(BaseModel):

    folder: str


class OpenRequest(BaseModel):

    platform: str
    path: str | None = None
    file_id: str | None = None
    # Preferred: the result's source_id (local path / Drive id / owner/repo:path).
    source_id: str | None = None
