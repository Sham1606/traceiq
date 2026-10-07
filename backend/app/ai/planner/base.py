"""Investigation Planner for TRACEIQ.

Produces a structured, evidence-driven InvestigationPlan determining domain investigator
sequencing, telemetry priorities, and dependencies based on observed evidence signals.
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import InvestigationPlan, InvestigationPlanStep
from ..validation import validate_plan


class InvestigationPlanner:
    """Plans investigator sequencing from normalized telemetry."""

    def create_plan(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
        investigation_id: str | None = None,
    ) -> InvestigationPlan:
        """Formulate an evidence-grounded, prioritized, validated investigation plan."""
        inv_id = investigation_id or incident.get("id") or str(uuid.uuid4())
        steps: list[InvestigationPlanStep] = []

        timeline_findings = evidence.get("timeline_findings", [])
        metric_findings = evidence.get("metric_findings", [])
        log_findings = evidence.get("log_findings", [])
        affected_services = incident.get("affected_services", [])

        # 1. Detect change events (deployments or configuration changes)
        has_change_event = any(
            t.get("event_type", "").lower() in {"deployment", "configuration"}
            for t in timeline_findings
        )
        change_reasons: list[str] = []
        if any(t.get("event_type", "").lower() == "deployment" for t in timeline_findings):
            change_reasons.append("production deployment event logged in timeline")
        if any(t.get("event_type", "").lower() == "configuration" for t in timeline_findings):
            change_reasons.append("configuration change event logged in timeline")

        # 2. Detect database telemetry signals
        db_metric_anomalies = [
            m for m in metric_findings
            if m.get("anomaly") and (
                "db" in m.get("service", "").lower()
                or "postgres" in m.get("service", "").lower()
                or "query" in m.get("metric", "").lower()
                or "connection" in m.get("metric", "").lower()
            )
        ]
        db_log_anomalies = [
            l for l in log_findings
            if (l.get("error_or_warn_count", 0) > 0) and (
                "db" in l.get("service", "").lower()
                or "postgres" in l.get("service", "").lower()
                or "connection" in l.get("event_type", "").lower()
            )
        ]
        has_db_signals = (
            bool(db_metric_anomalies)
            or bool(db_log_anomalies)
            or any("db" in s.lower() or "postgres" in s.lower() for s in affected_services)
        )

        # 3. Detect external dependency signals
        has_dep_event = any(
            t.get("event_type", "").lower() == "dependency" for t in timeline_findings
        )
        dep_metric_anomalies = [
            m for m in metric_findings
            if m.get("anomaly") and (
                "gateway_timeout" in m.get("metric", "").lower()
                or "egress" in m.get("metric", "").lower()
                or "third_party" in m.get("service", "").lower()
                or "external" in m.get("service", "").lower()
            )
        ]
        dep_log_anomalies = [
            l for l in log_findings
            if (l.get("error_or_warn_count", 0) > 0) and (
                "504" in l.get("summary", "")
                or "timeout" in l.get("summary", "").lower()
                or "third_party" in l.get("service", "").lower()
            )
        ]
        has_dependency = has_dep_event or bool(dep_metric_anomalies) or bool(dep_log_anomalies)

        # 4. Detect application telemetry signals
        app_metric_anomalies = [
            m for m in metric_findings
            if m.get("anomaly") and (
                m.get("metric") in {"error_rate", "request_latency", "http_5xx", "throughput"}
                or not ("db" in m.get("service", "").lower() or "postgres" in m.get("service", "").lower())
            )
        ]
        app_log_errors = [
            l for l in log_findings
            if l.get("error_or_warn_count", 0) > 0
            and not ("db" in l.get("service", "").lower() or "postgres" in l.get("service", "").lower())
        ]
        has_app_signals = bool(app_metric_anomalies) or bool(app_log_errors) or bool(affected_services)

        # --- Build Steps Grounded in Evidence ---

        # Deployment investigator: if release or config change observed
        if has_change_event:
            steps.append(
                InvestigationPlanStep(
                    step_id="step-deployment",
                    investigator_type="deployment",
                    reason=f"Change event detected ({', '.join(change_reasons)}); evaluate temporal alignment with degradation onset",
                    priority=1,
                    evidence_scope=["deployments", "configurations", "timeline"],
                    dependencies=[],
                    status="pending",
                )
            )

        # Database investigator: if DB metric/log signals detected
        if has_db_signals:
            db_reason = (
                f"Database telemetry anomalies observed ({len(db_metric_anomalies)} metric anomalies, "
                f"{len(db_log_anomalies)} log warnings); inspect query latency and connection pool saturation"
            )
            steps.append(
                InvestigationPlanStep(
                    step_id="step-database",
                    investigator_type="database",
                    reason=db_reason,
                    priority=1 if not has_change_event else 2,
                    evidence_scope=["metrics", "logs"],
                    dependencies=[],
                    status="pending",
                )
            )

        # Dependency investigator: if external failure or timeout signals detected
        if has_dependency:
            dep_reason = (
                "External dependency degradation signals observed in timeline and egress telemetry; "
                "evaluate downstream gateway timeouts and circuit breaker status"
            )
            steps.append(
                InvestigationPlanStep(
                    step_id="step-dependency",
                    investigator_type="dependency",
                    reason=dep_reason,
                    priority=1 if not has_change_event else 2,
                    evidence_scope=["dependencies", "timeline"],
                    dependencies=[],
                    status="pending",
                )
            )

        # Application investigator: if application-level errors or latency detected
        if has_app_signals:
            app_reason = (
                f"Application-level degradation detected across affected services "
                f"({', '.join(affected_services) if affected_services else 'active services'}); "
                f"evaluate error rate spikes, HTTP 5xx responses, and stack traces"
            )
            steps.append(
                InvestigationPlanStep(
                    step_id="step-application",
                    investigator_type="application",
                    reason=app_reason,
                    priority=1 if not (has_change_event or has_db_signals or has_dependency) else 2,
                    evidence_scope=["metrics", "logs"],
                    dependencies=[],
                    status="pending",
                )
            )

        # Fallback if no specific anomalies matched: ensure at least application domain is reviewed
        if not steps:
            steps.append(
                InvestigationPlanStep(
                    step_id="step-application",
                    investigator_type="application",
                    reason="Baseline application telemetry inspection for reported incident",
                    priority=1,
                    evidence_scope=["metrics", "logs"],
                    dependencies=[],
                    status="pending",
                )
            )

        # Domain investigator step IDs for dependency tracking
        domain_step_ids = [s.step_id for s in steps]

        # Correlation synthesis step (depends on domain investigators)
        step_corr_id = "step-correlation"
        steps.append(
            InvestigationPlanStep(
                step_id=step_corr_id,
                investigator_type="correlation",
                reason="Correlate cross-service telemetry deltas, timestamps, and causal cascades",
                priority=3,
                evidence_scope=["correlations", "timeline"],
                dependencies=domain_step_ids,
                status="pending",
            )
        )

        # Hypotheses generation step (depends on correlation)
        step_hyp_id = "step-hypotheses"
        steps.append(
            InvestigationPlanStep(
                step_id=step_hyp_id,
                investigator_type="hypotheses",
                reason="Formulate and rank competing root-cause hypotheses against evidence",
                priority=4,
                evidence_scope=["hypotheses", "evidence"],
                dependencies=[step_corr_id],
                status="pending",
            )
        )

        # Sort steps by priority ascending
        steps.sort(key=lambda s: s.priority)

        plan = InvestigationPlan(
            investigation_id=inv_id,
            steps=steps,
            status="planned",
        )

        # Validate the generated plan
        validate_plan(plan, evidence)
        return plan

