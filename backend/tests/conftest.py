"""Shared fixtures.

Every test gets a fresh in-memory SQLite database (never the real PostgreSQL), wired into
the app through FastAPI dependency overrides, and a pinned "today" so date rules are
deterministic.
"""

import os

# Must happen before `app` is imported: the module-level engine reads it.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.deps import get_today
from app.main import app

from helpers import TODAY, day


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection, so every session sees the same DB
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_today] = lambda: TODAY
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_room(client):
    counter = iter(range(100, 1000))

    def _make_room(**overrides):
        payload = {
            "number": str(next(counter)),
            "room_type": "DOUBLE",
            "floor": 1,
            "capacity": 2,
            "nightly_rate": 4000,
            **overrides,
        }
        response = client.post("/api/rooms", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_room


@pytest.fixture
def make_reservation(client, make_room):
    def _make_reservation(room=None, **overrides):
        room = room or make_room()
        payload = {
            "room_id": room["id"],
            "guest_name": "Priya Sharma",
            "guest_email": "priya@example.com",
            "guest_phone": "+91 90000 00000",
            "guests": 2,
            "check_in": day(0),
            "check_out": day(3),
            **overrides,
        }
        response = client.post("/api/reservations", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_reservation
