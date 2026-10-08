"""The one clock: timezone-aware UTC (the naive utcnow of the standard library is deprecated)."""

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:

    return datetime.now(timezone.utc)


def iso(value: Optional[datetime]) -> Optional[str]:
    """ISO 8601 with an explicit offset. Naive values (legacy) are UTC."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
