"""Tests for AI Investigation State creation, serialization, and typing."""
from datetime import datetime, timezone
import pytest
from app.ai.state import (
    IncidentContext,
    InvestigationStateModel,
    create_initial_state,
    deserialize_state,
    serialize_state,
)


@pytest.fixture
def sample_incident():
    return {
        "id": "inc-test-01",
        "scenario_id": "bad-deployment",
        "title": "Payment API Regression",
        "severity": "sev2",
        "started_at": datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
        "detected_at": datetime(2026, 10, 6, 14, 5, tzinfo=timezone.utc),
        "recovered_at": datetime(2026, 10, 6, 14, 30, tzinfo=timezone.utc),
        "affected_services": ["api-gateway", "payment-service"],
        "description": "Elevated error rate following release",
    }


@pytest.fixture
def sample_evidence():
    return {
        "scenario_id": "bad-deployment",
        "incident_id": "inc-test-01",
        "metric_findings": [
            {
                "id": "mf-01",
                "service": "payment-service",
                "metric": "error_rate",
                "baseline_mean": 0.001,
                "incident_mean": 0.125,
                "delta": 0.124,
                "delta_ratio": 124.0,
                "direction": "up",
                "anomaly": True,
                "source_ids": ["src-1"],
                "summary": "Critical error rate spike",
            }
        ],
        "timeline_findings": [
            {
                "id": "tl-01",
                "event_type": "deployment",
                "event_id": "dep-v4.2",
                "timestamp": "2026-10-06T13:58:00Z",
                "related_event_ids": [],
                "ordering": "t0 - 2m",
                "summary": "Deployment v4.2 applied",
            }
        ],
        "log_findings": [],
        "correlation_findings": [],
        "evidence": [
            {
                "id": "ev-01",
                "incident_id": "inc-test-01",
                "evidence_type": "metric",
                "source_id": "mf-01",
                "summary": "Error rate elevated",
                "strength": "strongly_supported",
                "supports": ["deployment_regression"],
                "contradicts": [],
            }
        ],
    }


def test_create_initial_state(sample_incident, sample_evidence):
    state = create_initial_state(sample_incident, sample_evidence, provider="mock", model="mock-reasoner")

    assert state["incident"]["id"] == "inc-test-01"
    assert state["incident"]["scenario_id"] == "bad-deployment"
    assert len(state["evidence"]["metric_findings"]) == 1
    assert state["plan"] is None
    assert state["hypotheses"] == []
    assert state["metadata"]["provider"] == "mock"
    assert state["metadata"]["model"] == "mock-reasoner"
    assert "planner" not in state["metadata"]["nodes_executed"]


def test_state_serialization_round_trip(sample_incident, sample_evidence):
    state = create_initial_state(sample_incident, sample_evidence)

    # Populate a test hypothesis and plan
    state["hypotheses"] = [
        {
            "id": "hyp-01",
            "title": "Application regression introduced by deployment",
            "explanation": "Deployment directly precedes metric anomaly.",
            "supporting_evidence_ids": ["ev-01"],
            "contradicting_evidence_ids": [],
            "missing_evidence": [],
            "reasoning_summary": "Telemetry correlates with release.",
            "strength": "strongly_supported",
        }
    ]

    json_str = serialize_state(state)
    assert isinstance(json_str, str)
    assert "hyp-01" in json_str

    model: InvestigationStateModel = deserialize_state(json_str)
    assert model.incident.id == "inc-test-01"
    assert len(model.hypotheses) == 1
    assert model.hypotheses[0].id == "hyp-01"
    assert model.hypotheses[0].strength == "strongly_supported"


def test_missing_optional_fields_handling(sample_incident, sample_evidence):
    minimal_incident = {
        "id": "inc-min-01",
        "scenario_id": "bad-deployment",
        "title": "Minimal Incident",
        "severity": "sev3",
        "started_at": datetime.now(timezone.utc),
        "detected_at": datetime.now(timezone.utc),
        "recovered_at": datetime.now(timezone.utc),
    }

    state = create_initial_state(minimal_incident, {"scenario_id": "bad-deployment", "incident_id": "inc-min-01"})
    assert state["incident"]["description"] == ""
    assert state["incident"]["affected_services"] == []
    assert state["challenge"] is None
    assert state["recovery"] is None
    assert state["errors"] == []
