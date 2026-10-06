"""B005: Recovery and audit tests — approval boundary, simulation, outcome, audit log."""
from __future__ import annotations

import pytest


BASE_INCIDENT = {
    "scenario_id": "bad-deployment",
    "title": "Recovery test incident",
    "severity": "sev2",
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
    "affected_services": ["api-gateway"],
    "description": "Test incident for recovery flow.",
}

SAFE_ACTION = {
    "action": "update config parameter max_connections",
    "target": "api-gateway",
    "rationale": "Config was changed before incident; reverting should restore baseline.",
}

UNSAFE_ACTION = {
    "action": "drop database payments_db",
    "target": "payments-db",
    "rationale": "Nuclear option — DO NOT USE",
}

ROLLBACK_ACTION = {
    "action": "rollback api-gateway to previous version",
    "target": "api-gateway",
    "rationale": "Deployment is the suspected root cause.",
}


@pytest.fixture()
def investigation_id(client):
    r_inc = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r_inc.status_code == 201
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r_inv.status_code == 201
    return r_inv.json()["id"]


@pytest.fixture()
def incident_id(client):
    r = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r.status_code == 201
    return r.json()["id"]


# --- Recovery action creation ---

def test_create_recovery_action(client, investigation_id):
    r = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    assert r.status_code == 201
    data = r.json()
    assert data["approval_status"] == "pending"
    assert data["simulated_result"] == "not_run"
    assert data["requires_human_approval"] is True


def test_list_recovery_actions(client, investigation_id):
    client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=ROLLBACK_ACTION)
    r = client.get(f"/api/v1/investigations/{investigation_id}/recovery-actions")
    assert r.status_code == 200
    assert len(r.json()) >= 2


# --- Approval gate ---

def test_approve_recovery_action(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/approve", json={"approved_by": "alice", "approved": True})
    assert r2.status_code == 200
    data = r2.json()
    assert data["approval_status"] == "approved"
    assert data["approved_by"] == "alice"
    assert data["approved_at"] is not None


def test_reject_recovery_action(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/approve", json={"approved_by": "bob", "approved": False})
    assert r2.status_code == 200
    assert r2.json()["approval_status"] == "rejected"


def test_double_approval_returns_409(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    approval = {"approved_by": "alice", "approved": True}
    client.post(f"/api/v1/recovery-actions/{action_id}/approve", json=approval)
    # Second approval must be rejected
    r3 = client.post(f"/api/v1/recovery-actions/{action_id}/approve", json=approval)
    assert r3.status_code == 409


# --- Simulation ---

def test_simulate_requires_approval(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    # Not approved yet — must be rejected
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/simulate")
    assert r2.status_code == 409


def test_simulate_safe_action(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    client.post(f"/api/v1/recovery-actions/{action_id}/approve", json={"approved_by": "alice", "approved": True})
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/simulate")
    assert r2.status_code == 200
    assert r2.json()["simulated_result"] == "safe"


def test_simulate_unsafe_action(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=UNSAFE_ACTION)
    action_id = r1.json()["id"]
    client.post(f"/api/v1/recovery-actions/{action_id}/approve", json={"approved_by": "alice", "approved": True})
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/simulate")
    assert r2.status_code == 200
    assert r2.json()["simulated_result"] == "unsafe"


def test_simulate_partial_action(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=ROLLBACK_ACTION)
    action_id = r1.json()["id"]
    client.post(f"/api/v1/recovery-actions/{action_id}/approve", json={"approved_by": "alice", "approved": True})
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/simulate")
    assert r2.status_code == 200
    assert r2.json()["simulated_result"] == "partial"


# --- Outcome ---

def test_record_outcome(client, investigation_id):
    r1 = client.post(f"/api/v1/investigations/{investigation_id}/recovery-actions", json=SAFE_ACTION)
    action_id = r1.json()["id"]
    r2 = client.post(f"/api/v1/recovery-actions/{action_id}/outcome?outcome=error+rate+normalised")
    assert r2.status_code == 200
    assert r2.json()["outcome"]


# --- Audit log ---

def test_audit_log_populated_after_investigation(client, incident_id):
    r_inv = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r_inv.status_code == 201

    r_audit = client.get(f"/api/v1/incidents/{incident_id}/audit")
    assert r_audit.status_code == 200
    entries = r_audit.json()
    assert len(entries) >= 1
    actions = [e["action"] for e in entries]
    assert any("investigation" in a for a in actions)


def test_audit_entries_have_required_fields(client, incident_id):
    client.post(f"/api/v1/incidents/{incident_id}/investigations")
    r = client.get(f"/api/v1/incidents/{incident_id}/audit")
    for entry in r.json():
        assert "id" in entry
        assert "incident_id" in entry
        assert "action" in entry
        assert "actor" in entry
        assert "created_at" in entry
