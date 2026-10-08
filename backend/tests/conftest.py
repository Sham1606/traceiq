"""Root conftest — shared fixtures for the full backend test suite.

Uses a dedicated PostgreSQL test database so integration tests match production.
The DATA_ROOT env var points to real generated data so the evidence engine runs.

Key design decisions:
- DATABASE_URL is overridden BEFORE any app imports so Settings picks up the test DB.
- init_db() runs during app import (in main.py) and creates tables on the test DB.
- All sessions use the same test DB engine, so data is consistent within each test.
- Tables are created clean at the start of the session and dropped after the session to clean up.
"""
from __future__ import annotations

import os
from pathlib import Path

# Set env vars BEFORE any app imports so Settings and the engine pick them up
DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "generated"
os.environ.setdefault("DATA_ROOT", str(DATA_ROOT))

# Use dedicated PostgreSQL test database
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+psycopg://traceiq:traceiq@127.0.0.1:5432/traceiq_test"),
)
os.environ["DATABASE_URL"] = TEST_DB_URL

import pytest
from fastapi.testclient import TestClient

# Import app modules AFTER env vars are set
import app.core.database as _db_module
from app.core.database import Base, get_db
from app.main import app  # init_db() is called inside main.py at import time


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    """Ensure all tables exist fresh on the test DB."""
    Base.metadata.drop_all(bind=_db_module.engine)
    Base.metadata.create_all(bind=_db_module.engine)
    yield
    Base.metadata.drop_all(bind=_db_module.engine)


@pytest.fixture()
def db():
    """Provide a DB session for direct service tests."""
    session = _db_module.SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    """TestClient using the configured test database."""
    with TestClient(app) as c:
        yield c
