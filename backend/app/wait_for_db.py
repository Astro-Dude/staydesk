"""Block until the database accepts connections (container start-up helper).

Usage: python -m app.wait_for_db   (timeout via DB_WAIT_TIMEOUT seconds, default 60)
"""

import os
import sys
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .db import engine


def wait_for_db(timeout: float, interval: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                print(f"database still unreachable after {timeout:.0f}s: {exc}", file=sys.stderr)
                return False
            print("waiting for database...", file=sys.stderr)
            time.sleep(interval)


if __name__ == "__main__":
    sys.exit(0 if wait_for_db(float(os.getenv("DB_WAIT_TIMEOUT", "60"))) else 1)
