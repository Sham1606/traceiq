"""Integration tests for LangGraph stateful orchestration and investigator failure isolation."""
from __future__ import annotations

import pytest
from app.ai.graph import run_investigation_graph
from app.ai.providers import MockAIProvider
from app.ai.state import create_initial_state


@pytest.fixture
def rich_telemetry_evidence():
    return {
        "evidence": [
            {
                "id": "ev-tl-01",
                "evidence_type": "timeline",
                "source_id": "dep-v4.2",
                "summary": "Deployment v4.2 canary deployed",
                "strength": "strongly_supported",
                "supports": ["deployment"],
                "contradicts": [],
            },
            {
                "id": "ev-met-01",
                "evidence_type": "metric",
                "source_id": "met-01",
                "summary": "5xx Error rate jumped from 0.001 to 0.142",
                "strength": "strongly_supported",
                "supports": ["error_rate"],
                "contradicts": [],
            },
            {
                "id": "ev-met-db",
                "evidence_type": "metric",
                "source_id": "met-db",
                "summary": "Database connection pool utilization reached 98%",
                "strength": "supported",
                "supports": ["connection_pool"],
                "contradicts": [],
            },
        ],
        "timeline_findings": [
            {"id": "tl-01", "event_type": "deployment", "event_id": "dep-v4.2", "summary": "Deployment v4.2 released"},
        ],
        "metric_findings": [
            {"id": "met-01", "service": "api-gateway", "metric": "error_rate", "anomaly": True},
            {"id": "met-db", "service": "order-db", "metric": "connection_pool", "anomaly": True},
        ],
        "log_findings": [
            {"id": "log-01", "service": "api-gateway", "error_or_warn_count": 22, "summary": "Unhandled exception"},
        ],
    }


@pytest.fixture
def test_incident():
    return {
        "id": "inc-orch-01",
        "scenario_id": "bad-deployment",
        "title": "Payment Outage",
        "severity": "sev1",
        "affected_services": ["api-gateway", "payment-service"],
    }


def test_full_langgraph_orchestration_populates_findings_and_plan(test_incident, rich_telemetry_evidence):
    initial_state = create_initial_state(test_incident, rich_telemetry_evidence)
    provider = MockAIProvider()

    final_state = run_investigation_graph(initial_state, provider=provider)

    assert final_state["plan"] is not None
    assert final_state["plan"]["status"] == "planned"

    # Verify findings collected
    findings = final_state.get("findings", [])
    assert len(findings) >= 2  # At least deployment and application were planned and executed

    finding_types = [f["investigator_type"] for f in findings]
    assert "deployment" in finding_types
    assert "application" in finding_types

    # Verify metadata nodes
    nodes = final_state["metadata"]["nodes_executed"]
    assert "planner" in nodes
    assert "investigate_deployment" in nodes
    assert "investigate_application" in nodes
    assert "collect_findings" in nodes
    assert "hypotheses" in nodes
    assert "evaluator" in nodes


def test_investigator_failure_isolation_does_not_break_other_investigators(test_incident, rich_telemetry_evidence):
    initial_state = create_initial_state(test_incident, rich_telemetry_evidence)

    # Configure mock provider to fail ONLY for database investigator
    failing_provider = MockAIProvider(failing_investigators={"database"})

    final_state = run_investigation_graph(initial_state, provider=failing_provider)

    # Investigation must still succeed
    assert final_state is not None

    # Errors must record the database failure
    errors = final_state.get("errors", [])
    db_errors = [e for e in errors if "database" in e.get("node_name", "")]
    assert len(db_errors) >= 1
    assert db_errors[0]["recovered"] is True

    # Other investigators (e.g. deployment and application) must still have succeeded
    findings = final_state.get("findings", [])
    finding_types = [f["investigator_type"] for f in findings]
    assert "deployment" in finding_types
    assert "application" in finding_types
    assert "database" not in finding_types  # No fake finding fabricated!
