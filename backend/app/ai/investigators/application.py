"""Application Investigator for TRACEIQ.

Analyzes application-level telemetry:
- HTTP status anomalies and 5xx error spikes
- Request latency degradation
- Service exceptions and application error logs
- Upstream and downstream service cascade behavior
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import EvidenceStrengthLabel, InvestigatorFinding
from .base import BaseInvestigator


class ApplicationInvestigator(BaseInvestigator):
    """Specialized investigator for application-layer errors and performance."""

    investigator_type: str = "application"
    domain: str = "application"

    def filter_evidence(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter telemetry to application service metrics, logs, and errors."""
        metric_findings = evidence.get("metric_findings", [])
        log_findings = evidence.get("log_findings", [])
        timeline_findings = evidence.get("timeline_findings", [])
        ev_items = evidence.get("evidence", [])

        # Filter out purely database or external infrastructure metrics
        app_metrics = [
            m for m in metric_findings
            if not ("db" in m.get("service", "").lower() or "postgres" in m.get("service", "").lower())
            and m.get("metric") in {"error_rate", "request_latency", "http_5xx", "throughput", "cpu_utilization"}
        ]

        app_logs = [
            l for l in log_findings
            if not ("db" in l.get("service", "").lower() or "postgres" in l.get("service", "").lower())
        ]

        app_timeline = [
            t for t in timeline_findings
            if t.get("event_type") in {"log", "alert"}
        ]

        app_evidence = [
            e for e in ev_items
            if e.get("evidence_type") in {"metric", "log"}
            and not ("db" in str(e.get("source_id", "")).lower() or "postgres" in str(e.get("source_id", "")).lower())
        ]

        return {
            "metrics": app_metrics,
            "logs": app_logs,
            "timeline": app_timeline,
            "evidence": app_evidence,
            "affected_services": incident.get("affected_services", []),
        }

    def build_deterministic_finding(
        self,
        incident: dict[str, Any],
        filtered_evidence: dict[str, Any],
        all_valid_ids: set[str],
    ) -> InvestigatorFinding:
        """Formulate evidence-grounded application finding."""
        metrics = filtered_evidence.get("metrics", [])
        logs = filtered_evidence.get("logs", [])
        ev_items = filtered_evidence.get("evidence", [])

        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []
        anomalies: list[str] = []

        # Collect supporting evidence IDs from filtered evidence items
        for item in ev_items:
            eid = str(item.get("id"))
            if eid in all_valid_ids:
                if item.get("strength") in {"strongly_supported", "supported"}:
                    supporting_ids.append(eid)
                elif item.get("contradicts"):
                    contradicting_ids.append(eid)

        # Check for error rate and latency anomalies
        error_rate_anomalies = [m for m in metrics if m.get("metric") == "error_rate" and m.get("anomaly")]
        latency_anomalies = [m for m in metrics if m.get("metric") == "request_latency" and m.get("anomaly")]
        error_logs = [l for l in logs if l.get("error_or_warn_count", 0) > 0]

        for m in error_rate_anomalies + latency_anomalies:
            mid = f"ev-{m.get('id')}"
            if mid in all_valid_ids and mid not in supporting_ids:
                supporting_ids.append(mid)
            anomalies.append(f"{m.get('service')}:{m.get('metric')}")

        for l in error_logs:
            lid = f"ev-{l.get('id')}"
            if lid in all_valid_ids and lid not in supporting_ids:
                supporting_ids.append(lid)

        # Determine strength and summary
        if error_rate_anomalies or (latency_anomalies and error_logs):
            strength: EvidenceStrengthLabel = "strongly_supported"
            title = "Severe application-layer error spike and latency degradation"
            summary = (
                f"Application telemetry indicates severe degradation across affected services. "
                f"Observed {len(error_rate_anomalies)} error rate spikes and {len(error_logs)} error log clusters."
            )
            reasoning = (
                "Observed HTTP 5xx errors and elevated failure rates directly impact user traffic. "
                "Stack traces and exception spikes confirm active application-layer degradation."
            )
        elif latency_anomalies:
            strength = "supported"
            title = "Elevated application request latency without primary error spikes"
            summary = f"Observed {len(latency_anomalies)} latency anomalies across application endpoints."
            reasoning = "Increased request latency indicates service slowness, potentially driven by downstream backpressure."
        else:
            strength = "inconclusive"
            title = "Application metrics within normal operating limits"
            summary = "No anomalous application error spikes or abnormal latencies detected."
            reasoning = "Application services report steady baselines; incident root cause likely external to application logic."

        return InvestigatorFinding(
            finding_id=f"find-app-{uuid.uuid4().hex[:6]}",
            investigator_type="application",
            domain="application",
            title=title,
            summary=summary,
            reasoning=reasoning,
            strength=strength,
            confidence_label=strength,
            evidence_ids=supporting_ids[:10],
            supporting_evidence_ids=supporting_ids[:10],
            contradicting_evidence_ids=contradicting_ids[:5],
            observations=[f"Monitored {len(metrics)} application metrics and {len(logs)} log categories."],
            uncertainties=["Determine if application error is trigger or cascade effect from backing dependencies."],
            anomalies_detected=anomalies[:5],
            metadata={"source": "deterministic_application_investigator"},
        )
