from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app


def test_health_reports_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_root_describes_service(client):
    body = client.get("/").json()
    assert body["service"] == "StayDesk API"
    assert body["docs"] == "/docs"


def test_meta_exposes_build_info(client):
    body = client.get("/api/meta").json()
    assert set(body) == {"service", "version", "git_sha"}


def test_ready_when_database_is_reachable(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_ready_returns_503_when_database_is_down(client):
    # A database without our tables behaves like an unmigrated / unreachable one.
    empty_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    broken = sessionmaker(bind=empty_engine)

    def broken_db():
        db = broken()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = broken_db
    response = client.get("/ready")
    empty_engine.dispose()
    assert response.status_code == 503
    assert response.json()["status"] == "NOT_READY"


def test_metrics_endpoint_is_prometheus_format(client, make_room):
    make_room()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert 'staydesk_reservation_events_total{event="created"}' in response.text
