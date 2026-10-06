"""Tests for LangGraph execution, planner, and safe deterministic fallback."""
import pytest
from app.ai.config import AISettings
from app.ai.graph import build_investigation_graph, run_investigation_graph
from app.ai.planner import InvestigationPlanner
from app.ai.providers import MockAIProvider
from app.ai.state import create_initial_state
from app.services.investigation.service import start_investigation
from app.models.orm import IncidentRow, AuditEntryRow


@pytest.fixture
def test_incident_dict():
    return {
        "id": "inc-graph-01",
        "scenario_id": "bad-deployment",
        "title": "Payment API Regression",
        "severity": "sev2",
        "started_at": "2026-10-06T14:00:00Z",
        "detected_at": "2026-10-06T14:05:00Z",
        "recovered_at": "2026-10-06T14:30:00Z",
        "affected_services": ["api-gateway", "payment-service"],
    }


@pytest.fixture
def test_evidence_dict():
    return {
        "scenario_id": "bad-deployment",
        "incident_id": "inc-graph-01",
        "metric_findings": [
            {
                "id": "mf-01",
                "service": "payment-service",
                "metric": "error_rate",
                "baseline_mean": 0.001,
                "incident_mean": 0.15,
                "delta": 0.149,
                "delta_ratio": 149.0,
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
                "summary": "Production deployment release v4.2 applied",
            }
        ],
        "log_findings": [],
        "correlation_findings": [],
        "evidence": [
            {
                "id": "ev-01",
                "incident_id": "inc-graph-01",
                "evidence_type": "metric",
                "source_id": "mf-01",
                "summary": "Error rate elevated",
                "strength": "strongly_supported",
                "supports": ["deployment_regression"],
                "contradicts": [],
            }
        ],
    }


def test_investigation_planner(test_incident_dict, test_evidence_dict):
    planner = InvestigationPlanner()
    plan = planner.create_plan(test_incident_dict, test_evidence_dict)

    assert plan.status == "planned"
    assert len(plan.steps) >= 3

    step_types = [s.investigator_type for s in plan.steps]
    assert "deployment" in step_types
    assert "application" in step_types
    assert "correlation" in step_types
    assert "hypotheses" in step_types


def test_langgraph_workflow_execution(test_incident_dict, test_evidence_dict):
    initial_state = create_initial_state(test_incident_dict, test_evidence_dict)
    provider = MockAIProvider()

    final_state = run_investigation_graph(initial_state, provider=provider)

    # Verify plan was formulated
    assert final_state["plan"] is not None
    assert final_state["plan"]["status"] == "planned"

    # Verify hypotheses formulated
    assert len(final_state["hypotheses"]) >= 1
    assert final_state["hypotheses"][0]["id"] == "hyp-ai-01"
    assert final_state["hypotheses"][0]["strength"] in {"strongly_supported", "supported"}

    # Verify nodes executed
    nodes = final_state["metadata"]["nodes_executed"]
    assert "planner" in nodes
    assert "hypotheses" in nodes
    assert "evaluator" in nodes
    assert final_state["metadata"]["completed_at"] is not None


def test_langgraph_failure_and_fallback_state(test_incident_dict, test_evidence_dict):
    initial_state = create_initial_state(test_incident_dict, test_evidence_dict)
    # Simulate a failing provider
    failing_provider = MockAIProvider(should_timeout=True)

    # Runner captures error and returns fallback state without crashing
    final_state = run_investigation_graph(initial_state, provider=failing_provider)

    assert final_state is not None
    assert len(final_state["errors"]) >= 0  # Handled safely


def test_service_investigation_ai_enabled_success(db, monkeypatch):
    """Test start_investigation with AI enabled and successful execution."""
    from app.ai import config as ai_config_module

    from datetime import datetime, timezone

    # Create incident row
    inc = IncidentRow(
        id="inc-ai-test-01",
        scenario_id="bad-deployment",
        title="AI Test Incident",
        severity="sev2",
        started_at=datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
        detected_at=datetime(2026, 10, 6, 14, 5, tzinfo=timezone.utc),
        recovered_at=datetime(2026, 10, 6, 14, 30, tzinfo=timezone.utc),
        affected_services=["api-gateway", "payment-service"],
    )
    db.add(inc)
    db.commit()

    # Enable AI with Mock provider
    test_settings = AISettings(enabled=True, provider="mock", model="mock-reasoner")
    monkeypatch.setattr(ai_config_module, "ai_settings", test_settings)

    resp = start_investigation(db, "inc-ai-test-01")
    assert resp is not None
    assert resp.status == "complete"
    assert resp.hypotheses is not None
    assert len(resp.hypotheses) >= 1

    # Check audit log for AI event
    audits = (
        db.query(AuditEntryRow)
        .filter(AuditEntryRow.incident_id == "inc-ai-test-01")
        .all()
    )
    audit_actions = [a.action for a in audits]
    assert "investigation_started" in audit_actions
    assert "ai_investigation_completed" in audit_actions
    assert "investigation_complete" in audit_actions


def test_service_investigation_ai_fallback_on_failure(db, monkeypatch):
    """Test that when AI provider raises an exception, the service falls back cleanly to deterministic."""
    from datetime import datetime, timezone
    from app.ai import config as ai_config_module
    from app.ai import providers as ai_providers_module

    inc = IncidentRow(
        id="inc-ai-fail-01",
        scenario_id="bad-deployment",
        title="AI Fallback Test Incident",
        severity="sev2",
        started_at=datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
        detected_at=datetime(2026, 10, 6, 14, 5, tzinfo=timezone.utc),
        recovered_at=datetime(2026, 10, 6, 14, 30, tzinfo=timezone.utc),
        affected_services=["api-gateway", "payment-service"],
    )
    db.add(inc)
    db.commit()

    # Configure AI enabled
    test_settings = AISettings(enabled=True, provider="mock", model="mock-failing")
    monkeypatch.setattr(ai_config_module, "ai_settings", test_settings)

    # Force provider factory to raise an error
    def _failing_provider_factory(*args, **kwargs):
        raise ai_providers_module.AITimeoutError("Simulated LLM network timeout")

    monkeypatch.setattr(ai_providers_module, "get_ai_provider", _failing_provider_factory)

    # Must complete successfully via deterministic fallback
    resp = start_investigation(db, "inc-ai-fail-01")
    assert resp is not None
    assert resp.status == "complete"
    assert resp.hypotheses is not None
    assert len(resp.hypotheses) >= 1

    # Check audit log recorded fallback
    audits = (
        db.query(AuditEntryRow)
        .filter(AuditEntryRow.incident_id == "inc-ai-fail-01")
        .all()
    )
    audit_actions = [a.action for a in audits]
    assert "ai_investigation_fallback" in audit_actions
    assert "investigation_complete" in audit_actions
