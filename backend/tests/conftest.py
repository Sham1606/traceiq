"""Root conftest — shared fixtures for the full backend test suite.

Uses a file-based SQLite test database so tests are isolated and fast.
The DATA_ROOT env var points to real generated data so the evidence engine runs.

Key design decisions:
- DATABASE_URL is overridden BEFORE any app imports so Settings picks up the test DB.
- init_db() runs during app import (in main.py) and creates tables on the test DB.
- All sessions use the same test DB engine, so data is consistent within each test.
- Tables are dropped after the session to clean up.
"""
from __future__ import annotations

import os
from pathlib import Path

# Set env vars BEFORE any app imports so Settings and the engine pick them up
DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "generated"
os.environ.setdefault("DATA_ROOT", str(DATA_ROOT))
# Use file-based SQLite so multiple connections in the same process share state
os.environ["DATABASE_URL"] = "sqlite:///./test_traceiq.db"

import pytest
from fastapi.testclient import TestClient

# Import app modules AFTER env vars are set
import app.core.database as _db_module
from app.core.database import Base, get_db
from app.main import app  # init_db() is called inside main.py at import time


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    """Ensure all tables exist on the test DB."""
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
