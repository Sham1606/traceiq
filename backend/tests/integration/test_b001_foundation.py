"""B001: Foundation tests — startup, health, config."""
from __future__ import annotations

import os


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert "version" in data


def test_health_version_matches_config(client):
    from app.core.config import settings
    response = client.get("/health")
    assert response.json()["version"] == settings.app_version


def test_openapi_schema_available(client):
    """App must expose OpenAPI schema — confirms FastAPI started correctly."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "TRACEIQ"


def test_config_data_root_exists():
    from app.core.config import settings
    assert settings.data_root.exists(), (
        f"DATA_ROOT {settings.data_root} does not exist. Run scripts/generate_data.py first."
    )


def test_config_database_url_set():
    from app.core.config import settings
    assert settings.database_url, "DATABASE_URL must not be empty"


def test_unknown_route_returns_404(client):
    response = client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404
