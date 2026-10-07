"""Unit tests for the four specialized AI domain investigators."""
from __future__ import annotations

import pytest
from app.ai.investigators import (
    ApplicationInvestigator,
    DatabaseInvestigator,
    DeploymentInvestigator,
    DependencyInvestigator,
)
from app.ai.validation import AIValidationError


@pytest.fixture
def mock_evidence_bundle():
    return {
        "evidence": [
            {
                "id": "ev-met-01",
                "evidence_type": "metric",
                "source_id": "met-01",
                "summary": "error_rate spiked from 0.001 to 0.124 on payment-service",
                "strength": "strongly_supported",
                "supports": ["error_rate"],
                "contradicts": [],
            },
            {
                "id": "ev-met-db-01",
                "evidence_type": "metric",
                "source_id": "met-db-01",
                "summary": "query_latency increased by 800% on postgres-db",
                "strength": "strongly_supported",
                "supports": ["query_latency"],
                "contradicts": [],
            },
            {
                "id": "ev-tl-dep-01",
                "evidence_type": "timeline",
                "source_id": "dep-v4.2",
                "summary": "Deployment v4.2 deployed to payment-service at 14:02:00Z",
                "strength": "supported",
                "supports": ["deployment"],
                "contradicts": [],
            },
            {
                "id": "ev-tl-ext-01",
                "evidence_type": "timeline",
                "source_id": "dep-gate-01",
                "summary": "External gateway degraded at 14:05:00Z with 504 status",
                "strength": "supported",
                "supports": ["dependency"],
                "contradicts": [],
            },
        ],
        "metric_findings": [
            {"id": "met-01", "service": "payment-service", "metric": "error_rate", "anomaly": True},
            {"id": "met-db-01", "service": "postgres-db", "metric": "query_latency", "anomaly": True},
        ],
        "log_findings": [
            {"id": "log-01", "service": "payment-service", "error_or_warn_count": 15, "summary": "NullPointerException in PaymentFilter"},
        ],
        "timeline_findings": [
            {"id": "tl-01", "event_type": "deployment", "event_id": "dep-v4.2", "summary": "Deployment v4.2 released"},
            {"id": "tl-02", "event_type": "dependency", "event_id": "dep-gate-01", "summary": "Gateway 504 Timeout"},
        ],
    }


@pytest.fixture
def sample_incident():
    return {
        "id": "inc-inv-test",
        "scenario_id": "test-scenario",
        "title": "Payment Regression",
        "severity": "sev1",
        "affected_services": ["payment-service"],
    }


def test_application_investigator_filtered_scope_and_finding(sample_incident, mock_evidence_bundle):
    inv = ApplicationInvestigator()
    filtered = inv.filter_evidence(sample_incident, mock_evidence_bundle)

    # Verification of input boundary: database metrics must NOT be in application metrics
    db_services = [m["service"] for m in filtered["metrics"] if "db" in m["service"] or "postgres" in m["service"]]
    assert len(db_services) == 0

    finding = inv.investigate(sample_incident, mock_evidence_bundle)
    assert finding.investigator_type == "application"
    assert finding.domain == "application"
    assert finding.strength in {"strongly_supported", "supported"}
    assert len(finding.supporting_evidence_ids) >= 1
    # Evidence reference must be valid
    for eid in finding.supporting_evidence_ids:
        assert eid in {"ev-met-01", "met-01", "ev-log-01", "log-01"}


def test_database_investigator_filtered_scope_and_finding(sample_incident, mock_evidence_bundle):
    inv = DatabaseInvestigator()
    filtered = inv.filter_evidence(sample_incident, mock_evidence_bundle)

    # Database metrics must be present
    assert any("postgres" in m["service"] or "query" in m["metric"] for m in filtered["metrics"])

    finding = inv.investigate(sample_incident, mock_evidence_bundle)
    assert finding.investigator_type == "database"
    assert finding.domain == "database"
    assert finding.strength in {"strongly_supported", "supported"}
    assert "ev-met-db-01" in finding.supporting_evidence_ids or "met-db-01" in finding.supporting_evidence_ids


def test_deployment_investigator_temporal_reasoning(sample_incident, mock_evidence_bundle):
    inv = DeploymentInvestigator()
    filtered = inv.filter_evidence(sample_incident, mock_evidence_bundle)

    assert any(t["event_type"] == "deployment" for t in filtered["timeline"])

    finding = inv.investigate(sample_incident, mock_evidence_bundle)
    assert finding.investigator_type == "deployment"
    assert finding.domain == "deployment"
    assert finding.strength in {"strongly_supported", "supported"}
    assert "precedes" in finding.title.lower() or "deployment" in finding.title.lower()


def test_dependency_investigator_findings(sample_incident, mock_evidence_bundle):
    inv = DependencyInvestigator()
    filtered = inv.filter_evidence(sample_incident, mock_evidence_bundle)

    assert any(t["event_type"] == "dependency" for t in filtered["timeline"])

    finding = inv.investigate(sample_incident, mock_evidence_bundle)
    assert finding.investigator_type == "dependency"
    assert finding.domain == "dependency"
    assert finding.strength in {"strongly_supported", "supported"}
    assert len(finding.supporting_evidence_ids) >= 1


def test_investigator_missing_evidence_returns_inconclusive(sample_incident):
    empty_evidence = {
        "evidence": [],
        "metric_findings": [],
        "log_findings": [],
        "timeline_findings": [],
    }

    db_inv = DatabaseInvestigator()
    finding = db_inv.investigate(sample_incident, empty_evidence)
    assert finding.strength == "inconclusive"
    assert "healthy" in finding.title.lower() or "no" in finding.title.lower()


def test_investigator_rejects_hallucinated_evidence_id(sample_incident, mock_evidence_bundle):
    from app.ai.schemas import InvestigatorFinding
    from app.ai.validation import validate_finding_references, extract_valid_evidence_ids

    valid_ids = extract_valid_evidence_ids(mock_evidence_bundle)
    fake_finding = InvestigatorFinding(
        finding_id="find-fake",
        investigator_type="application",
        domain="application",
        title="Fake Finding",
        summary="Summary",
        supporting_evidence_ids=["ev-hallucinated-id-999"],
    )

    with pytest.raises(AIValidationError) as exc:
        validate_finding_references(fake_finding, valid_ids)
    assert "ev-hallucinated-id-999" in str(exc.value)
