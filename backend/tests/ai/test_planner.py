"""Unit tests for Investigation Planner reasoning, evidence inspection, and validation rules."""
from __future__ import annotations

import pytest
from app.ai.planner import InvestigationPlanner
from app.ai.schemas import InvestigationPlan, InvestigationPlanStep
from app.ai.validation import AIValidationError, validate_plan


@pytest.fixture
def sample_incident():
    return {
        "id": "inc-plan-01",
        "scenario_id": "test-scenario",
        "title": "Service Anomaly Incident",
        "severity": "sev2",
        "affected_services": ["api-gateway", "order-service"],
    }


def test_planner_creates_evidence_driven_plan_for_deployment(sample_incident):
    evidence = {
        "timeline_findings": [
            {"id": "tl-01", "event_type": "deployment", "event_id": "v2.1", "summary": "Release v2.1 deployed"},
        ],
        "metric_findings": [
            {"id": "mf-01", "service": "api-gateway", "metric": "error_rate", "anomaly": True},
        ],
        "log_findings": [
            {"id": "lf-01", "service": "api-gateway", "error_or_warn_count": 5},
        ],
    }

    planner = InvestigationPlanner()
    plan = planner.create_plan(sample_incident, evidence)

    assert plan.status == "planned"
    types = [s.investigator_type for s in plan.steps]
    assert "deployment" in types
    assert "application" in types

    dep_step = next(s for s in plan.steps if s.investigator_type == "deployment")
    assert "deployment event" in dep_step.reason.lower()
    assert dep_step.priority == 1


def test_planner_creates_evidence_driven_plan_for_database(sample_incident):
    evidence = {
        "timeline_findings": [],
        "metric_findings": [
            {
                "id": "mf-db-01",
                "service": "postgres-db",
                "metric": "query_latency",
                "anomaly": True,
            },
            {
                "id": "mf-db-02",
                "service": "postgres-db",
                "metric": "connection_pool_utilization",
                "anomaly": True,
            },
        ],
        "log_findings": [
            {"id": "lf-db-01", "service": "postgres-db", "error_or_warn_count": 8, "event_type": "connection_pool"},
        ],
    }

    planner = InvestigationPlanner()
    plan = planner.create_plan(sample_incident, evidence)

    types = [s.investigator_type for s in plan.steps]
    assert "database" in types
    assert "deployment" not in types  # No deployment event exists

    db_step = next(s for s in plan.steps if s.investigator_type == "database")
    assert db_step.priority == 1
    assert "database" in db_step.reason.lower()


def test_planner_creates_evidence_driven_plan_for_dependency(sample_incident):
    evidence = {
        "timeline_findings": [
            {"id": "tl-dep-01", "event_type": "dependency", "event_id": "ext-gate", "summary": "Payment gateway degraded"},
        ],
        "metric_findings": [
            {"id": "mf-dep-01", "service": "third_party", "metric": "gateway_timeout", "anomaly": True},
        ],
        "log_findings": [
            {"id": "lf-dep-01", "service": "third_party", "error_or_warn_count": 12, "summary": "HTTP 504 Gateway Timeout"},
        ],
    }

    planner = InvestigationPlanner()
    plan = planner.create_plan(sample_incident, evidence)

    types = [s.investigator_type for s in plan.steps]
    assert "dependency" in types
    dep_step = next(s for s in plan.steps if s.investigator_type == "dependency")
    assert dep_step.priority == 1
    assert "dependency" in dep_step.reason.lower()


def test_plan_validation_rejects_duplicate_investigator_types():
    invalid_plan = InvestigationPlan(
        investigation_id="inv-dup",
        steps=[
            InvestigationPlanStep(
                step_id="step-1",
                investigator_type="database",
                reason="Reason 1",
                priority=1,
            ),
            InvestigationPlanStep(
                step_id="step-2",
                investigator_type="database",
                reason="Reason 2",
                priority=2,
            ),
        ],
    )
    with pytest.raises(AIValidationError) as exc:
        validate_plan(invalid_plan)
    assert "Duplicate investigator_type" in str(exc.value)


def test_plan_validation_rejects_empty_reason():
    invalid_plan = InvestigationPlan(
        investigation_id="inv-empty-reason",
        steps=[
            InvestigationPlanStep(
                step_id="step-1",
                investigator_type="application",
                reason="   ",
                priority=1,
            ),
        ],
    )
    with pytest.raises(AIValidationError) as exc:
        validate_plan(invalid_plan)
    assert "non-empty reason" in str(exc.value)


def test_plan_validation_rejects_circular_dependencies():
    # Circular: step-1 depends on step-2, and step-2 depends on step-1
    circular_plan = InvestigationPlan(
        investigation_id="inv-circ",
        steps=[
            InvestigationPlanStep(
                step_id="step-1",
                investigator_type="application",
                reason="App evaluation",
                priority=1,
                dependencies=["step-2"],
            ),
            InvestigationPlanStep(
                step_id="step-2",
                investigator_type="database",
                reason="DB evaluation",
                priority=2,
                dependencies=["step-1"],
            ),
        ],
    )
    with pytest.raises(AIValidationError) as exc:
        validate_plan(circular_plan)
    assert "Circular dependency" in str(exc.value)


def test_plan_validation_rejects_invalid_priority():
    with pytest.raises(Exception):
        InvestigationPlanStep(
            step_id="step-1",
            investigator_type="application",
            reason="App evaluation",
            priority=15,  # > 10 is invalid
        )
