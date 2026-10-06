from __future__ import annotations

from pathlib import Path

from .correlation import correlate
from .loader import load_scenario
from .logs import analyze_logs
from .metrics import analyze_metrics
from .models import EvidenceBundle
from .normalize import normalize
from .strength import build_evidence
from .timeline import correlate_timeline


class EvidenceEngine:
    """Deterministic evidence engine. It never calls an LLM and never reads ground truth."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)

    def investigate(self, scenario_id: str) -> EvidenceBundle:
        data = load_scenario(self.data_root, scenario_id)
        normalized = normalize(
            data.metrics,
            data.logs,
            data.deployments,
            data.configuration_changes,
            data.dependencies,
        )
        metrics = analyze_metrics(normalized.metrics, data.incident.started_at, data.incident.recovered_at)
        logs = analyze_logs(list(normalized.logs), data.incident.started_at, data.incident.recovered_at)
        timeline = correlate_timeline(
            data.incident.started_at,
            data.incident.recovered_at,
            normalized.deployments,
            normalized.configurations,
            normalized.dependencies,
            normalized.logs,
        )
        correlations = correlate(metrics, logs, timeline)
        evidence = build_evidence(metrics, logs, correlations, data.incident.id)
        return EvidenceBundle(
            scenario_id=scenario_id,
            incident_id=data.incident.id,
            metric_findings=metrics,
            timeline_findings=timeline,
            log_findings=logs,
            correlation_findings=correlations,
            evidence=evidence,
        )
