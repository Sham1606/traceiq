from __future__ import annotations

from traceiq_data.schemas import EvidenceStrength
from .models import CorrelationFinding, EvidenceBundle, LogFinding, MetricFinding


def classify_metric(finding: MetricFinding) -> EvidenceStrength:
    if not finding.anomaly:
        return EvidenceStrength.INCONCLUSIVE
    ratio = abs(finding.delta_ratio or 0)
    if ratio >= 1.0 or (finding.metric == "error_rate" and finding.delta >= 0.08):
        return EvidenceStrength.STRONGLY_SUPPORTED
    if ratio >= 0.5:
        return EvidenceStrength.SUPPORTED
    return EvidenceStrength.WEAKLY_SUPPORTED


def build_evidence(metric_findings: list[MetricFinding], log_findings: list[LogFinding], correlations: list[CorrelationFinding], incident_id: str) -> list[dict]:
    evidence = []
    for finding in metric_findings:
        evidence.append({
            "id": f"ev-{finding.id}",
            "incident_id": incident_id,
            "evidence_type": "metric",
            "source_id": finding.id,
            "summary": finding.summary,
            "strength": classify_metric(finding).value,
            "supports": [finding.metric] if finding.anomaly else [],
            "contradicts": [],
        })
    for finding in log_findings:
        strength = EvidenceStrength.SUPPORTED if finding.error_or_warn_count >= 5 else EvidenceStrength.WEAKLY_SUPPORTED
        evidence.append({
            "id": f"ev-{finding.id}",
            "incident_id": incident_id,
            "evidence_type": "log",
            "source_id": finding.id,
            "summary": finding.summary,
            "strength": strength.value,
            "supports": [finding.event_type] if finding.error_or_warn_count else [],
            "contradicts": [],
        })
    for finding in correlations:
        evidence.append({
            "id": f"ev-{finding.id}",
            "incident_id": incident_id,
            "evidence_type": "timeline",
            "source_id": finding.id,
            "summary": finding.summary,
            "strength": EvidenceStrength.SUPPORTED.value,
            "supports": finding.supports,
            "contradicts": finding.contradicts,
        })
    return evidence
