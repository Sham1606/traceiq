"""TRACEIQ FastAPI application entry point (B001).

Startup initialises the database. Health endpoint exposes DB reachability.
"""
from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, init_db
from app.schemas.api import HealthResponse
from app.api.incidents import router as incidents_router
from app.api.investigations import router as investigations_router
from app.api.memory import router as memory_router
from app.api.recovery import router as recovery_router

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Synthetic-data-driven collaborative AI incident investigation platform.",
)

# Initialise tables on startup (idempotent)
init_db()

# Register routers
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(recovery_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Liveness + DB connectivity check."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "error"

    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(status=overall, version=settings.app_version, db=db_status)
