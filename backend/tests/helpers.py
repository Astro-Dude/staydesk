from datetime import date, timedelta

# Pinned "today" for every test, so date rules (arrivals, past check-ins) are deterministic.
TODAY = date(2026, 3, 10)


def day(offset: int) -> str:
    """ISO date `offset` days from the pinned today."""
    return (TODAY + timedelta(days=offset)).isoformat()
