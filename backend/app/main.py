from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .deps import DbSession
from .models import Room
from .routers import dashboard, reservations, rooms

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Front-office API for StayDesk: rooms, reservations, check-in/out and occupancy.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Probes and the scrape itself would drown out real traffic in the request metrics.
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

app.include_router(rooms.router)
app.include_router(reservations.router)
app.include_router(dashboard.router)


@app.get("/", tags=["meta"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/api/meta", tags=["meta"])
def meta():
    """Build info, shown in the UI so a rollout can be traced to a commit."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "git_sha": settings.git_sha,
    }


@app.get("/health", tags=["probes"])
def health():
    """Liveness: the process is up and serving HTTP. Deliberately does not touch the DB."""
    return {"status": "UP"}


@app.get("/ready", tags=["probes"])
def ready(db: DbSession):
    """Readiness: the database is reachable and migrated, so traffic can be served."""
    try:
        db.execute(select(Room.id).limit(1))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "NOT_READY", "reason": "database unavailable"},
        )
    return {"status": "READY"}
