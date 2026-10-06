"""Investigation Planner foundation for TRACEIQ.

Produces a structured InvestigationPlan determining domain investigator sequencing,
telemetry priorities, and dependencies based on observed evidence signals.
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import InvestigationPlan, InvestigationPlanStep


class InvestigationPlanner:
    """Plans investigator sequencing from normalized telemetry."""

    def create_plan(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
        investigation_id: str | None = None,
    ) -> InvestigationPlan:
        """Formulate a prioritized, structured investigation plan."""
        inv_id = investigation_id or incident.get("id") or str(uuid.uuid4())
        steps: list[InvestigationPlanStep] = []

        timeline_findings = evidence.get("timeline_findings", [])
        metric_findings = evidence.get("metric_findings", [])
        affected_services = incident.get("affected_services", [])

        has_deployment = any(
            t.get("event_type", "").lower() == "deployment" for t in timeline_findings
        )
        has_db_signals = (
            any(
                "db" in m.get("service", "").lower()
                or "postgres" in m.get("service", "").lower()
                or "query" in m.get("metric", "").lower()
                for m in metric_findings
            )
            or any("db" in s.lower() for s in affected_services)
        )
        has_dependency = any(
            t.get("event_type", "").lower() == "dependency" for t in timeline_findings
        )

        dep_step_ids: list[str] = []

        # 1. Deployment investigation (high priority if release event found)
        if has_deployment:
            step_id = "step-deployment"
            steps.append(
                InvestigationPlanStep(
                    step_id=step_id,
                    investigator_type="deployment",
                    reason="Production deployment event logged in timeline; evaluate revision deltas",
                    priority=1,
                    dependencies=[],
                    status="pending",
                )
            )
            dep_step_ids.append(step_id)

        # 2. Application investigator (always active for service telemetry)
        step_app_id = "step-application"
        steps.append(
            InvestigationPlanStep(
                step_id=step_app_id,
                investigator_type="application",
                reason="Evaluate application log spikes, exception patterns, and request error rates",
                priority=1,
                dependencies=[],
                status="pending",
            )
        )
        dep_step_ids.append(step_app_id)

        # 3. Database investigator (if DB anomalies or services observed)
        if has_db_signals:
            step_id = "step-database"
            steps.append(
                InvestigationPlanStep(
                    step_id=step_id,
                    investigator_type="database",
                    reason="Database telemetry anomalies observed; inspect query latency and connection pool saturation",
                    priority=2,
                    dependencies=[],
                    status="pending",
                )
            )
            dep_step_ids.append(step_id)

        # 4. Dependency investigator (if third-party egress or timeouts logged)
        if has_dependency:
            step_id = "step-dependency"
            steps.append(
                InvestigationPlanStep(
                    step_id=step_id,
                    investigator_type="dependency",
                    reason="External service events observed; evaluate egress timeout and circuit breaker telemetry",
                    priority=2,
                    dependencies=[],
                    status="pending",
                )
            )
            dep_step_ids.append(step_id)

        # 5. Correlation step (depends on domain investigators)
        step_corr_id = "step-correlation"
        steps.append(
            InvestigationPlanStep(
                step_id=step_corr_id,
                investigator_type="correlation",
                reason="Correlate cross-service telemetry deltas, timestamps, and causal cascades",
                priority=3,
                dependencies=dep_step_ids,
                status="pending",
            )
        )

        # 6. Hypotheses generation (depends on correlation)
        step_hyp_id = "step-hypotheses"
        steps.append(
            InvestigationPlanStep(
                step_id=step_hyp_id,
                investigator_type="hypotheses",
                reason="Formulate and rank competing root-cause hypotheses against evidence",
                priority=4,
                dependencies=[step_corr_id],
                status="pending",
            )
        )

        return InvestigationPlan(
            investigation_id=inv_id,
            steps=steps,
            status="planned",
        )
