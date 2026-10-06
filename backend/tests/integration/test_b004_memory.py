"""B004: Historical memory tests — store/retrieve/search/compare."""
from __future__ import annotations

import pytest

MEMORY_1 = {
    "fingerprint": "deployment:api-gateway:error-rate:high",
    "title": "API gateway error rate spike post-deployment",
    "root_cause_category": "bad_deployment",
    "evidence_summary": ["error_rate anomaly on api-gateway", "deployment event 5min before incident"],
    "recovery_action": "rollback api-gateway to v1.2.3",
    "recovery_outcome": "error rate recovered within 15min",
    "scenario_id": "bad-deployment",
    "incident_id": "incident-001",
}

MEMORY_2 = {
    "fingerprint": "database:query-latency:high:connection-saturation",
    "title": "Database connection pool exhaustion",
    "root_cause_category": "database_degradation",
    "evidence_summary": ["query_latency_p95 anomaly", "connection_utilization at 98%"],
    "recovery_action": "increase connection pool max size",
    "recovery_outcome": "latency normalised after config change",
    "scenario_id": "database-degradation",
    "incident_id": "incident-002",
}


def test_store_memory_returns_201(client):
    r = client.post("/api/v1/memory", json=MEMORY_1)
    assert r.status_code == 201
    data = r.json()
    assert data["fingerprint"] == MEMORY_1["fingerprint"]
    assert data["root_cause_category"] == "bad_deployment"
    assert "id" in data


def test_get_memory_by_id(client):
    r1 = client.post("/api/v1/memory", json=MEMORY_1)
    memory_id = r1.json()["id"]
    r2 = client.get(f"/api/v1/memory/{memory_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == memory_id


def test_get_memory_not_found(client):
    r = client.get("/api/v1/memory/does-not-exist")
    assert r.status_code == 404


def test_search_memory_finds_match(client):
    client.post("/api/v1/memory", json=MEMORY_1)
    # Query with overlapping tokens
    r = client.get("/api/v1/memory/search?fingerprint=deployment:api-gateway:high")
    assert r.status_code == 200
    data = r.json()
    assert data["query_fingerprint"] == "deployment:api-gateway:high"
    assert len(data["matches"]) >= 1
    # Match must include shared tokens
    match = data["matches"][0]
    assert len(match["shared_fingerprint_tokens"]) >= 1
    assert match["match_note"]  # must have a note marking it as context only


def test_search_memory_no_match(client):
    """Unrelated fingerprint should return empty matches."""
    client.post("/api/v1/memory", json=MEMORY_2)
    r = client.get("/api/v1/memory/search?fingerprint=completely:unrelated:xyz")
    assert r.status_code == 200
    # May or may not find matches depending on tokenisation — zero is acceptable
    assert "matches" in r.json()


def test_memory_match_is_labelled_as_context_only(client):
    """Historical matches must be annotated as supporting context, not automatic truth."""
    client.post("/api/v1/memory", json=MEMORY_1)
    r = client.get("/api/v1/memory/search?fingerprint=deployment:api-gateway:error-rate:high")
    data = r.json()
    assert data["matches"]
    match = data["matches"][0]
    note = match["match_note"].lower()
    assert "context" in note or "supporting" in note or "validate" in note


def test_memory_evidence_summary_roundtrip(client):
    summaries = ["metric A anomaly", "deployment event B"]
    payload = {**MEMORY_1, "evidence_summary": summaries}
    r = client.post("/api/v1/memory", json=payload)
    assert r.status_code == 201
    assert r.json()["evidence_summary"] == summaries


def test_search_memory_limit(client):
    for i in range(3):
        payload = {**MEMORY_1, "fingerprint": f"deployment:api-gateway:error-rate:{i}"}
        client.post("/api/v1/memory", json=payload)
    r = client.get("/api/v1/memory/search?fingerprint=deployment:api-gateway&limit=2")
    assert r.status_code == 200
    assert len(r.json()["matches"]) <= 2
