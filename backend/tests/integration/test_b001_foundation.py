"""B001: Foundation tests — startup, health, config."""
from __future__ import annotations

import os
import pytest


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert "version" in data
    assert data["ai_mode"] in {"mock", "gemini", "deterministic", "unavailable"}


@pytest.mark.parametrize(
    ("enabled", "provider", "api_key", "model", "expected_mode"),
    [
        (False, "gemini", "test-key", "configured-model", "deterministic"),
        (True, "mock", None, "mock-reasoner", "mock"),
        (True, "gemini", None, "configured-model", "unavailable"),
        (True, "gemini", "test-key", "configured-model", "gemini"),
    ],
)
def test_health_ai_mode_reflects_configuration(
    client, monkeypatch, enabled, provider, api_key, model, expected_mode
):
    from app.main import ai_settings

    monkeypatch.setattr(ai_settings, "enabled", enabled)
    monkeypatch.setattr(ai_settings, "provider", provider)
    monkeypatch.setattr(ai_settings, "gemini_api_key", api_key)
    monkeypatch.setattr(ai_settings, "model", model)

    assert client.get("/health").json()["ai_mode"] == expected_mode


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
