from pydantic import BaseModel


class SchedulerRequest(BaseModel):

    priority_platform: str
    platforms: list[str]