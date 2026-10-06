"""B002: Incident API tests — create/list/get with validation."""
from __future__ import annotations

from datetime import datetime, timezone


BASE_INCIDENT = {
    "scenario_id": "bad-deployment",
    "title": "API gateway error rate spike",
    "severity": "sev2",
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
    "affected_services": ["api-gateway", "order-service"],
    "description": "Error rate jumped to 15% after deployment.",
}


def test_create_incident_returns_201(client):
    response = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert response.status_code == 201
    data = response.json()
    assert data["scenario_id"] == "bad-deployment"
    assert data["status"] == "open"
    assert data["severity"] == "sev2"
    assert "id" in data
    assert "created_at" in data


def test_create_incident_persists(client):
    r1 = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r1.status_code == 201
    incident_id = r1.json()["id"]

    r2 = client.get(f"/api/v1/incidents/{incident_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == incident_id


def test_list_incidents(client):
    # Create two incidents
    for _ in range(2):
        client.post("/api/v1/incidents", json=BASE_INCIDENT)

    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 2


def test_get_nonexistent_incident_returns_404(client):
    response = client.get("/api/v1/incidents/does-not-exist")
    assert response.status_code == 404


def test_create_incident_missing_required_field_returns_422(client):
    bad = {k: v for k, v in BASE_INCIDENT.items() if k != "title"}
    response = client.post("/api/v1/incidents", json=bad)
    assert response.status_code == 422


def test_create_incident_invalid_severity_returns_422(client):
    bad = {**BASE_INCIDENT, "severity": "critical"}  # not a valid literal
    response = client.post("/api/v1/incidents", json=bad)
    assert response.status_code == 422


def test_create_incident_detected_before_started_returns_422(client):
    bad = {
        **BASE_INCIDENT,
        "started_at": "2024-03-15T10:10:00Z",
        "detected_at": "2024-03-15T10:00:00Z",  # earlier than started_at
    }
    response = client.post("/api/v1/incidents", json=bad)
    assert response.status_code == 422


def test_list_incidents_pagination(client):
    # Create 3 incidents
    for i in range(3):
        payload = {**BASE_INCIDENT, "title": f"Incident {i}"}
        client.post("/api/v1/incidents", json=payload)

    r1 = client.get("/api/v1/incidents?skip=0&limit=2")
    assert r1.status_code == 200
    assert len(r1.json()["items"]) <= 2

    r2 = client.get("/api/v1/incidents?limit=0")
    assert r2.status_code == 422  # limit must be >= 1


def test_incident_affected_services_roundtrip(client):
    services = ["svc-a", "svc-b", "svc-c"]
    payload = {**BASE_INCIDENT, "affected_services": services}
    r = client.post("/api/v1/incidents", json=payload)
    assert r.status_code == 201
    assert r.json()["affected_services"] == services
