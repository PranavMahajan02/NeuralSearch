"""The one clock: timezone-aware UTC (the naive utcnow of the standard library is deprecated)."""

from datetime import UTC, datetime


def utcnow() -> datetime:

    return datetime.now(UTC)


def iso(value: datetime | None) -> str | None:
    """ISO 8601 with an explicit offset. Naive values (legacy) are UTC."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
