from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db


def get_today() -> date:
    """Current calendar date at the hotel. A dependency so tests can pin the clock."""
    return datetime.now(ZoneInfo(settings.hotel_timezone)).date()


DbSession = Annotated[Session, Depends(get_db)]
Today = Annotated[date, Depends(get_today)]
