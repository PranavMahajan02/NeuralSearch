from pydantic import BaseModel, Field

from app.models.platforms import PlatformName


class SchedulerRequest(BaseModel):

    priority_platform: PlatformName
    platforms: list[PlatformName] = Field(min_length=1)
