"""Tests for Ground Truth Isolation and Protection in AI Layer."""
import pytest
from app.ai.ground_truth import (
    assert_no_ground_truth,
    contains_ground_truth,
    sanitize_evidence_payload,
)
from app.ai.state import create_initial_state


@pytest.fixture
def contaminated_payload():
    return {
        "scenario_id": "bad-deployment",
        "incident_id": "inc-01",
        "evidence": [
            {"id": "ev-01", "summary": "Metric delta observed"}
        ],
        # Hidden ground truth fields that must NEVER enter AI reasoning:
        "root_cause_service": "payment-service",
        "contradictory_lead": "database timeout was normal",
        "expected_recovery_action": "rollback",
        "primary_evidence_ids": ["ev-01", "ev-02"],
        "ground_truth": {
            "root_cause": "bad release v4.2"
        },
    }


def test_contains_ground_truth_detects_forbidden_fields(contaminated_payload):
    assert contains_ground_truth(contaminated_payload) is True


def test_assert_no_ground_truth_raises_on_contamination(contaminated_payload):
    with pytest.raises(ValueError) as exc_info:
        assert_no_ground_truth(contaminated_payload)
    assert "Forbidden ground truth detected" in str(exc_info.value)


def test_sanitize_evidence_payload_strips_all_hidden_fields(contaminated_payload):
    clean = sanitize_evidence_payload(contaminated_payload)

    # Legitimate fields preserved
    assert clean["scenario_id"] == "bad-deployment"
    assert clean["incident_id"] == "inc-01"
    assert len(clean["evidence"]) == 1

    # Hidden fields completely removed
    assert "root_cause_service" not in clean
    assert "contradictory_lead" not in clean
    assert "expected_recovery_action" not in clean
    assert "primary_evidence_ids" not in clean
    assert "ground_truth" not in clean

    # Clean payload passes assert_no_ground_truth
    assert_no_ground_truth(clean)
    assert contains_ground_truth(clean) is False


def test_create_initial_state_sanitizes_ground_truth(contaminated_payload):
    incident = {
        "id": "inc-01",
        "scenario_id": "bad-deployment",
        "title": "Test Incident",
        "severity": "sev2",
        "started_at": "2026-10-06T14:00:00Z",
        "detected_at": "2026-10-06T14:05:00Z",
        "recovered_at": "2026-10-06T14:30:00Z",
    }

    state = create_initial_state(incident, contaminated_payload)

    # State evidence must not contain any forbidden fields
    assert "root_cause_service" not in state["evidence"]
    assert "contradictory_lead" not in state["evidence"]
    assert "ground_truth" not in state["evidence"]
    assert contains_ground_truth(state["evidence"]) is False
