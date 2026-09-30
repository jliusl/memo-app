from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware UTC now.

    Timestamps are generated in Python rather than with a SQL `now()` default so that
    a freshly written row already carries its final values: the response never needs a
    follow-up SELECT, and a caller can never observe a stale `updated_at`.
    """
    return datetime.now(UTC)
