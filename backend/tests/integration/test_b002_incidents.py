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


def test_live_custom_evidence_persists_through_investigation_retrieval(client):
    evidence_items = [
        {
            "id": "custom-metric-01",
            "type": "metric",
            "service": "orders-db",
            "metric": "connection_pool_utilization",
            "baseline": 30,
            "incident": 94,
            "value": 94,
            "summary": "Connection pool utilization increased during the incident.",
        },
        {
            "id": "custom-log-01",
            "type": "log",
            "service": "order-service",
            "event_type": "upstream_timeout",
            "count": 4,
            "summary": "Upstream timeout events appeared during order submission.",
        },
        {
            "id": "custom-metric-02",
            "type": "metric",
            "service": "orders-db",
            "metric": "cpu_utilization",
            "timestamp": "2026-10-09T18:10:00Z",
            "baseline": 42,
            "incident": 42,
            "value": 42,
            "anomaly": False,
            "summary": "orders-db CPU utilization measured 42% at 18:10.",
        },
        {
            "id": "custom-metric-03",
            "type": "metric",
            "service": "order-service",
            "metric": "request_latency_ms",
            "timestamp": "2026-10-09T18:16:00Z",
            "baseline": 50,
            "incident": 240,
            "value": 240,
            "delta_ratio": 3.8,
            "summary": "order-service request latency increased 380% at 18:16.",
        },
        {
            "id": "custom-metric-04",
            "type": "metric",
            "service": "api-gateway",
            "metric": "http_5xx_rate",
            "timestamp": "2026-10-09T18:17:00Z",
            "baseline": 0.05,
            "incident": 0.17,
            "value": 0.17,
            "delta_ratio": 2.4,
            "summary": "api-gateway error rate increased 240% at 18:17.",
        },
        {
            "id": "custom-deployment-absence",
            "type": "deployment",
            "service": "order-service",
            "timestamp": "2026-10-09T18:18:00Z",
            "summary": "No deployment was reported during the observed incident window.",
        },
        {
            "id": "custom-dependency-normal",
            "type": "dependency",
            "service": "payment-provider-api",
            "timestamp": "2026-10-09T18:18:00Z",
            "summary": "External dependency health was reported within normal operating range.",
        },
    ]
    created = client.post(
        "/api/v1/incidents/live",
        json={
            "title": "Custom evidence persistence test",
            "severity": "sev2",
            "affected_services": ["orders-db", "order-service"],
            "description": "Verify supplied evidence survives the custom workflow.",
            "evidence_items": evidence_items,
        },
    )

    assert created.status_code == 201
    incident = created.json()
    incident_id = incident["id"]
    assert incident["scenario_id"] == "LIVE_CUSTOM"
    assert incident["custom_evidence"] == evidence_items
    assert "root_cause_service" not in created.text
    assert "expected_recovery_action" not in created.text
    assert "primary_evidence_ids" not in created.text
    assert "ground_truth" not in created.text

    retrieved_incident = client.get(f"/api/v1/incidents/{incident_id}")
    assert retrieved_incident.status_code == 200
    assert retrieved_incident.json()["custom_evidence"] == evidence_items

    started = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert started.status_code == 201
    investigation = started.json()
    assert investigation["status"] == "complete"
    evidence = investigation["evidence"]
    assert evidence["ai_telemetry"]["mode"] == "mock"
    assert evidence["plan"]["steps"]
    findings = evidence["investigator_findings"]
    assert {finding["investigator_type"] for finding in findings} >= {"application", "database"}
    assert len(investigation["hypotheses"]) >= 1
    assert investigation["challenge"] is not None
    assert not any(
        item["event_type"] == "deployment" for item in evidence["timeline_findings"]
    )
    assert not any(
        "introduced by recent deployment" in hypothesis["title"].lower()
        for hypothesis in investigation["hypotheses"]
    )
    evidence_ids = {item["id"] for item in evidence["evidence"]}
    source_ids = {source_id for item in evidence["evidence"] for source_id in item["source_ids"]}
    expected_evidence_ids = {item["id"] for item in evidence_items}
    assert expected_evidence_ids.issubset(evidence_ids)
    assert expected_evidence_ids.issubset(source_ids)
    for finding in findings:
        assert set(finding["evidence_ids"]).issubset(evidence_ids)
    for hypothesis in investigation["hypotheses"]:
        assert set(hypothesis["supporting_evidence_ids"]).issubset(evidence_ids)
        assert set(hypothesis["contradicting_evidence_ids"]).issubset(evidence_ids)
    assert set(investigation["challenge"]["independent_evidence_ids"]).issubset(evidence_ids)
    for hidden_key in (
        "root_cause_service",
        "expected_recovery_action",
        "primary_evidence_ids",
        "ground_truth",
    ):
        assert hidden_key not in started.text

    listed = client.get(f"/api/v1/incidents/{incident_id}/investigations")
    assert listed.status_code == 200
    assert listed.json()[0]["evidence"] == evidence


def test_custom_incident_rejects_ground_truth_before_persistence(client):
    payload = {
        "title": "Custom evidence with forbidden ground truth",
        "severity": "sev1",
        "affected_services": ["payment-service"],
        "evidence_items": [
            {
                "type": "metric",
                "service": "payment-service",
                "ground_truth": {"root_cause_service": "payment-service"},
            }
        ],
    }

    response = client.post("/api/v1/incidents/live", json=payload)

    assert response.status_code == 422
    assert "Custom evidence with forbidden ground truth" not in str(
        [item["title"] for item in client.get("/api/v1/incidents?limit=200").json()["items"]]
    )


def test_regular_incident_custom_evidence_rejects_ground_truth(client):
    payload = {
        **BASE_INCIDENT,
        "title": "Regular incident with forbidden custom evidence",
        "custom_evidence": [{"ground_truth": {"expected_recovery_action": "rollback"}}],
    }

    response = client.post("/api/v1/incidents", json=payload)

    assert response.status_code == 422
    assert "Regular incident with forbidden custom evidence" not in str(
        [item["title"] for item in client.get("/api/v1/incidents?limit=200").json()["items"]]
    )
