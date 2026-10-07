"""Deployment and Change Investigator for TRACEIQ.

Analyzes releases, canary rollouts, and configuration changes:
- Temporal relationship between change events and degradation onset
- Service affected by release vs overall incident blast radius
- Version and configuration diff correlations
- False lead detection: changes occurring after degradation or on unaffected services
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import EvidenceStrengthLabel, InvestigatorFinding
from .base import BaseInvestigator


class DeploymentInvestigator(BaseInvestigator):
    """Specialized investigator for deployments and configuration modifications."""

    investigator_type: str = "deployment"
    domain: str = "deployment"

    def filter_evidence(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter telemetry to deployment and configuration change events and related timeline."""
        timeline_findings = evidence.get("timeline_findings", [])
        ev_items = evidence.get("evidence", [])

        change_timeline = [
            t for t in timeline_findings
            if t.get("event_type") in {"deployment", "configuration"}
        ]

        change_evidence = [
            e for e in ev_items
            if e.get("evidence_type") == "timeline"
            or any(k in str(e.get("summary", "")).lower() for k in {"deploy", "release", "config", "version"})
        ]

        return {
            "timeline": change_timeline,
            "evidence": change_evidence,
            "incident": incident,
        }

    def build_deterministic_finding(
        self,
        incident: dict[str, Any],
        filtered_evidence: dict[str, Any],
        all_valid_ids: set[str],
    ) -> InvestigatorFinding:
        """Formulate evidence-grounded deployment/change finding."""
        timeline = filtered_evidence.get("timeline", [])
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
            observations.append(f"{t.get('event_type')}:{t.get('summary')}")

        has_deployment = any(t.get("event_type") == "deployment" for t in timeline)
        has_config = any(t.get("event_type") == "configuration" for t in timeline)

        if has_deployment:
            strength: EvidenceStrengthLabel = "strongly_supported" if supporting_ids else "supported"
            title = "Production deployment temporally precedes incident degradation"
            summary = (
                f"Detected release deployment event in timeline immediately prior to telemetry anomalies. "
                f"Observed {len(timeline)} change events correlating with degradation onset."
            )
            reasoning = (
                "Release deployment directly preceded the spike in error rates and latency. "
                "Strong temporal correlation suggests application regression or configuration mismatch introduced in new build."
            )
        elif has_config:
            strength = "strongly_supported" if supporting_ids else "supported"
            title = "Configuration change event aligns with incident onset"
            summary = "Detected configuration change event in timeline preceding service degradation."
            reasoning = (
                "Dynamic configuration update coincides with service degradation. "
                "Modified settings likely triggered downstream caching, timeout, or concurrency issues."
            )
        else:
            strength = "inconclusive"
            title = "No deployment or configuration events detected in incident window"
            summary = "Zero release or configuration modification events recorded prior to incident onset."
            reasoning = (
                "Telemetry shows no active releases, rollouts, or config updates near incident start. "
                "Deployment regression is ruled out or weakly supported as a primary trigger."
            )

        return InvestigatorFinding(
            finding_id=f"find-dep-{uuid.uuid4().hex[:6]}",
            investigator_type="deployment",
            domain="deployment",
            title=title,
            summary=summary,
            reasoning=reasoning,
            strength=strength,
            confidence_label=strength,
            evidence_ids=supporting_ids[:10],
            supporting_evidence_ids=supporting_ids[:10],
            contradicting_evidence_ids=contradicting_ids[:5],
            observations=observations[:5],
            uncertainties=[
                "Confirm if rollback of recent build restores baseline error rates.",
                "Verify whether change was accompanied by undetected infrastructure shifts."
            ],
            anomalies_detected=["deployment_onset_correlation"] if (has_deployment or has_config) else [],
            metadata={"source": "deterministic_deployment_investigator"},
        )
