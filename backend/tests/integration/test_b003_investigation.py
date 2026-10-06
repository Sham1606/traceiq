"""B003: Investigation service tests — success, failure, hypothesis generation."""
from __future__ import annotations

import pytest

BASE_INCIDENT = {
    "scenario_id": "bad-deployment",
    "title": "Error rate spike",
    "severity": "sev2",
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
    "affected_services": ["api-gateway"],
    "description": "Test incident for investigation.",
}


@pytest.fixture()
def incident_id(client):
    r = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r.status_code == 201
    return r.json()["id"]


def test_start_investigation_returns_201(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["incident_id"] == incident_id
    assert data["id"]
    assert data["status"] in {"complete", "failed"}


def test_start_investigation_complete_has_evidence(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "complete", f"Investigation failed: {data}"
    assert data["evidence"] is not None
    assert "metric_findings" in data["evidence"]
    assert data["evidence"]["metric_findings"]


def test_start_investigation_complete_has_hypotheses(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "complete"
    assert data["hypotheses"] is not None
    assert len(data["hypotheses"]) >= 1
    h = data["hypotheses"][0]
    assert "id" in h
    assert "title" in h
    assert "strength" in h
    assert h["strength"] in {
        "strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"
    }


def test_investigation_does_not_expose_ground_truth(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    text = r.text.lower()
    # Ground truth fields must never appear in investigation responses
    assert "root_cause_service" not in text
    assert "contradictory_lead" not in text
    assert "expected_recovery_action" not in text
    assert "primary_evidence_ids" not in text


def test_start_investigation_nonexistent_incident_returns_404(client):
    r = client.post("/api/v1/incidents/does-not-exist/investigations")
    assert r.status_code == 404


def test_get_investigation(client, incident_id):
    r1 = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    inv_id = r1.json()["id"]
    r2 = client.get(f"/api/v1/investigations/{inv_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == inv_id


def test_list_investigations_for_incident(client, incident_id):
    client.post(f"/api/v1/incidents/{incident_id}/investigations")
    client.post(f"/api/v1/incidents/{incident_id}/investigations")
    r = client.get(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


def test_investigation_with_bad_scenario_records_failure(client):
    """When scenario data is missing, investigation status must be 'failed', not a 500."""
    bad_incident = {
        **BASE_INCIDENT,
        "scenario_id": "nonexistent-scenario",
        "title": "Bad scenario",
    }
    r = client.post("/api/v1/incidents", json=bad_incident)
    incident_id = r.json()["id"]

    r2 = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r2.status_code == 201
    assert r2.json()["status"] == "failed"


def test_investigation_for_database_degradation_scenario(client):
    """Database degradation scenario should find DB metric anomalies."""
    payload = {
        **BASE_INCIDENT,
        "scenario_id": "database-degradation",
        "title": "DB degradation test",
    }
    r = client.post("/api/v1/incidents", json=payload)
    inc_id = r.json()["id"]

    r2 = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r2.status_code == 201
    data = r2.json()
    assert data["status"] == "complete"
    # At least one hypothesis should mention database
    hyps = data["hypotheses"]
    titles = [h["title"].lower() for h in hyps]
    assert any("database" in t or "db" in t for t in titles)
