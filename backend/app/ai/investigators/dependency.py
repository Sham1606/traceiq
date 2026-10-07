"""Dependency Investigator for TRACEIQ.

Analyzes third-party and internal downstream dependencies:
- External payment gateways, auth providers, and partner API telemetry
- 504 Gateway Timeouts, socket disconnects, and egress latency anomalies
- Circuit breaker trip states and connection retry loops
- Causal analysis: Did external failure cause internal failure, or vice-versa?
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import EvidenceStrengthLabel, InvestigatorFinding
from .base import BaseInvestigator


class DependencyInvestigator(BaseInvestigator):
    """Specialized investigator for external and downstream dependency failures."""

    investigator_type: str = "dependency"
    domain: str = "dependency"

    def filter_evidence(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter telemetry to dependency events, egress latency, and gateway timeout logs."""
        metric_findings = evidence.get("metric_findings", [])
        log_findings = evidence.get("log_findings", [])
        timeline_findings = evidence.get("timeline_findings", [])
        ev_items = evidence.get("evidence", [])

        dep_timeline = [
            t for t in timeline_findings
            if t.get("event_type") == "dependency"
        ]

        dep_metrics = [
            m for m in metric_findings
            if any(k in m.get("metric", "").lower() for k in {"gateway_timeout", "egress", "external"})
            or any(k in m.get("service", "").lower() for k in {"third_party", "external", "gateway", "stripe"})
        ]

        dep_logs = [
            l for l in log_findings
            if any(k in l.get("summary", "").lower() for k in {"504", "gateway timeout", "upstream", "circuit breaker", "third_party", "external"})
            or any(k in l.get("service", "").lower() for k in {"third_party", "external"})
        ]

        dep_evidence = [
            e for e in ev_items
            if any(k in str(e.get("summary", "")).lower() for k in {"dependency", "gateway", "504", "external", "third-party"})
        ]

        return {
            "timeline": dep_timeline,
            "metrics": dep_metrics,
            "logs": dep_logs,
            "evidence": dep_evidence,
            "incident": incident,
        }

    def build_deterministic_finding(
        self,
        incident: dict[str, Any],
        filtered_evidence: dict[str, Any],
        all_valid_ids: set[str],
    ) -> InvestigatorFinding:
        """Formulate evidence-grounded dependency finding."""
        timeline = filtered_evidence.get("timeline", [])
        metrics = filtered_evidence.get("metrics", [])
        logs = filtered_evidence.get("logs", [])
        ev_items = filtered_evidence.get("evidence", [])

        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []
        observations: list[str] = []

        for item in ev_items:
            eid = str(item.get("id"))
            if eid in all_valid_ids:
                if item.get("strength") in {"strongly_supported", "supported"}:
                    supporting_ids.append(eid)
                elif item.get("contradicts"):
                    contradicting_ids.append(eid)

        for t in timeline:
            tid = f"ev-{t.get('id')}"
            if tid in all_valid_ids and tid not in supporting_ids:
                supporting_ids.append(tid)
            raw_tid = str(t.get("id"))
            if raw_tid in all_valid_ids and raw_tid not in supporting_ids:
                supporting_ids.append(raw_tid)
            observations.append(f"dependency_event:{t.get('summary')}")

        for m in metrics:
            if m.get("anomaly"):
                mid = f"ev-{m.get('id')}"
                if mid in all_valid_ids and mid not in supporting_ids:
                    supporting_ids.append(mid)

        for l in logs:
            lid = f"ev-{l.get('id')}"
            if lid in all_valid_ids and lid not in supporting_ids:
                supporting_ids.append(lid)

        has_dep_event = bool(timeline)
        has_dep_logs = bool(logs)
        has_dep_metrics = any(m.get("anomaly") for m in metrics)

        if has_dep_event or (has_dep_logs and has_dep_metrics):
            strength: EvidenceStrengthLabel = "strongly_supported" if supporting_ids else "supported"
            title = "External downstream dependency failure and gateway timeout cascade"
            summary = (
                f"Observed external dependency degradation: {len(timeline)} timeline events, "
                f"{len(logs)} gateway timeout log patterns, and elevated egress response latencies."
            )
            reasoning = (
                "Third-party partner service or external gateway experienced failure, "
                "leading to HTTP 504 Gateway Timeouts, thread pool starvation, and cascading failure internally."
            )
        elif has_dep_logs:
            strength = "supported"
            title = "Isolated dependency timeout logs detected"
            summary = "Encountered downstream dependency warnings without confirmed total provider outage."
            reasoning = "Downstream timeout logs suggest transient partner network instability."
        else:
            strength = "inconclusive"
            title = "External dependencies healthy; no third-party degradation observed"
            summary = "Third-party APIs and outbound gateways respond normally within SLA."
            reasoning = "Telemetry indicates external partner endpoints are healthy and responding with standard latencies."

        return InvestigatorFinding(
            finding_id=f"find-depend-{uuid.uuid4().hex[:6]}",
            investigator_type="dependency",
            domain="dependency",
            title=title,
            summary=summary,
            reasoning=reasoning,
            strength=strength,
            confidence_label=strength,
            evidence_ids=supporting_ids[:10],
            supporting_evidence_ids=supporting_ids[:10],
            contradicting_evidence_ids=contradicting_ids[:5],
            observations=observations[:5],
            uncertainties=["Confirm whether circuit breaker opened properly to isolate upstream caller."],
            anomalies_detected=["dependency_timeout_cascade"] if (has_dep_event or has_dep_logs) else [],
            metadata={"source": "deterministic_dependency_investigator"},
        )
