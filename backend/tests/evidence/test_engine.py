from pathlib import Path

import pytest

from app.evidence import EvidenceEngine


DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "generated"
SCENARIOS = ["bad-deployment", "database-degradation", "external-dependency", "configuration-regression"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_engine_runs_without_ground_truth(scenario):
    result = EvidenceEngine(DATA_ROOT).investigate(scenario)
    assert result.scenario_id == scenario
    assert result.metric_findings
    assert result.log_findings
    assert result.evidence


def test_database_degradation_exposes_db_anomaly():
    result = EvidenceEngine(DATA_ROOT).investigate("database-degradation")
    metrics = {(x.service, x.metric): x for x in result.metric_findings}
    assert metrics[("payments-db", "query_latency_p95")].anomaly
    assert metrics[("payments-db", "connection_utilization")].anomaly


def test_external_dependency_exposes_failed_dependency():
    result = EvidenceEngine(DATA_ROOT).investigate("external-dependency")
    dependency_events = [x for x in result.timeline_findings if x.event_type == "dependency"]
    assert dependency_events


def test_configuration_change_is_visible_in_timeline():
    result = EvidenceEngine(DATA_ROOT).investigate("configuration-regression")
    assert any(x.event_type == "configuration" for x in result.timeline_findings)


def test_metric_evidence_has_explainable_strength():
    result = EvidenceEngine(DATA_ROOT).investigate("bad-deployment")
    strengths = {item["strength"] for item in result.evidence}
    assert strengths <= {"strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"}
