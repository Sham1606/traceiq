"""LangGraph investigation workflow builder for TRACEIQ.

Orchestrates stateful execution:
START
  ↓
planner
  ↓
investigator dispatch (deployment, database, dependency, application)
  ↓
collect_findings & validate
  ↓
correlation (Phase 5.3: cross-investigator evidence correlation)
  ↓
historical_context (Phase 5.3: historical incident reasoning)
  ↓
hypotheses (Phase 5.3: competing hypotheses generation)
  ↓
challenge (Phase 5.3: adversarial hypothesis challenge)
  ↓
evaluator
  ↓
END
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from langgraph.graph import StateGraph, START, END

from ..challenge import challenge_hypothesis
from ..correlation import correlate_findings
from ..historical import (
    build_fingerprint_from_evidence,
    build_historical_context_note,
    enrich_hypotheses_with_historical_context,
)
from ..investigators import (
    ApplicationInvestigator,
    DatabaseInvestigator,
    DeploymentInvestigator,
    DependencyInvestigator,
)
from ..planner import InvestigationPlanner
from ..providers.base import AIProvider
from ..schemas import AIHypothesis, CorrelationFinding, InvestigationPlan, InvestigatorFinding
from ..state import InvestigationState
from ..validation import (
    extract_valid_evidence_ids,
    validate_finding_references,
    validate_hypothesis_references,
)

logger = logging.getLogger("traceiq.ai.graph")


def build_investigation_graph(provider: AIProvider | None = None) -> Any:
    """Build and compile the LangGraph investigation workflow."""
    planner = InvestigationPlanner()
    app_inv = ApplicationInvestigator()
    db_inv = DatabaseInvestigator()
    dep_inv = DeploymentInvestigator()
    depend_inv = DependencyInvestigator()

    # ------------------------------------------------------------------ #
    # Node 1: Investigation Planner                                        #
    # ------------------------------------------------------------------ #
    def planner_node(state: InvestigationState) -> dict[str, Any]:
        """Node 1: Plan investigation sequence from normalized evidence."""
        incident = state.get("incident", {})
        evidence = state.get("evidence", {})
        plan = planner.create_plan(incident, evidence)

        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("planner")
        metadata["nodes_executed"] = nodes_executed

        return {
            "plan": plan.model_dump(mode="json"),
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Nodes 2a-2d: Domain Investigators                                   #
    # ------------------------------------------------------------------ #
    def investigate_deployment_node(state: InvestigationState) -> dict[str, Any]:
        """Node 2a: Deployment and configuration change investigator."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("investigate_deployment")
        metadata["nodes_executed"] = nodes_executed

        plan_data = state.get("plan") or {}
        steps = plan_data.get("steps", [])
        is_planned = any(s.get("investigator_type") == "deployment" for s in steps)
        if not is_planned:
            return {"metadata": metadata}

        findings = list(state.get("findings", []))
        errors = list(state.get("errors", []))

        try:
            finding = dep_inv.investigate(
                incident=state.get("incident", {}),
                evidence=state.get("evidence", {}),
                provider=provider,
            )
            findings.append(finding.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Deployment investigator encountered isolated failure: %s", e)
            errors.append({
                "node_name": "investigate_deployment",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })

        return {
            "findings": findings,
            "errors": errors,
            "metadata": metadata,
        }

    def investigate_database_node(state: InvestigationState) -> dict[str, Any]:
        """Node 2b: Database telemetry and connection health investigator."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("investigate_database")
        metadata["nodes_executed"] = nodes_executed

        plan_data = state.get("plan") or {}
        steps = plan_data.get("steps", [])
        is_planned = any(s.get("investigator_type") == "database" for s in steps)
        if not is_planned:
            return {"metadata": metadata}

        findings = list(state.get("findings", []))
        errors = list(state.get("errors", []))

        try:
            finding = db_inv.investigate(
                incident=state.get("incident", {}),
                evidence=state.get("evidence", {}),
                provider=provider,
            )
            findings.append(finding.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Database investigator encountered isolated failure: %s", e)
            errors.append({
                "node_name": "investigate_database",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })

        return {
            "findings": findings,
            "errors": errors,
            "metadata": metadata,
        }

    def investigate_dependency_node(state: InvestigationState) -> dict[str, Any]:
        """Node 2c: External downstream dependency investigator."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("investigate_dependency")
        metadata["nodes_executed"] = nodes_executed

        plan_data = state.get("plan") or {}
        steps = plan_data.get("steps", [])
        is_planned = any(s.get("investigator_type") == "dependency" for s in steps)
        if not is_planned:
            return {"metadata": metadata}

        findings = list(state.get("findings", []))
        errors = list(state.get("errors", []))

        try:
            finding = depend_inv.investigate(
                incident=state.get("incident", {}),
                evidence=state.get("evidence", {}),
                provider=provider,
            )
            findings.append(finding.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Dependency investigator encountered isolated failure: %s", e)
            errors.append({
                "node_name": "investigate_dependency",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })

        return {
            "findings": findings,
            "errors": errors,
            "metadata": metadata,
        }

    def investigate_application_node(state: InvestigationState) -> dict[str, Any]:
        """Node 2d: Application-layer performance and error investigator."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("investigate_application")
        metadata["nodes_executed"] = nodes_executed

        plan_data = state.get("plan") or {}
        steps = plan_data.get("steps", [])
        is_planned = any(s.get("investigator_type") == "application" for s in steps)
        if not is_planned:
            return {"metadata": metadata}

        findings = list(state.get("findings", []))
        errors = list(state.get("errors", []))

        try:
            finding = app_inv.investigate(
                incident=state.get("incident", {}),
                evidence=state.get("evidence", {}),
                provider=provider,
            )
            findings.append(finding.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Application investigator encountered isolated failure: %s", e)
            errors.append({
                "node_name": "investigate_application",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })

        return {
            "findings": findings,
            "errors": errors,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Node 3: Collect & validate findings                                  #
    # ------------------------------------------------------------------ #
    def collect_findings_node(state: InvestigationState) -> dict[str, Any]:
        """Node 3: Validate and aggregate domain findings into shared state."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("collect_findings")
        metadata["nodes_executed"] = nodes_executed

        evidence = state.get("evidence", {})
        valid_ids = extract_valid_evidence_ids(evidence)
        findings = list(state.get("findings", []))

        validated_findings = []
        for f_data in findings:
            f_model = InvestigatorFinding.model_validate(f_data)
            validate_finding_references(f_model, valid_ids)
            validated_findings.append(f_model.model_dump(mode="json"))

        return {
            "findings": validated_findings,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Node 4 (Phase 5.3): Cross-investigator correlation                  #
    # ------------------------------------------------------------------ #
    def correlation_node(state: InvestigationState) -> dict[str, Any]:
        """Node 4 (5.3): Deterministic cross-investigator evidence correlation."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("correlation")
        metadata["nodes_executed"] = nodes_executed

        evidence = state.get("evidence", {})
        findings = state.get("findings", [])
        errors = list(state.get("errors", []))
        correlations = list(state.get("correlations", []))

        try:
            corr = correlate_findings(findings=findings, evidence=evidence)
            correlations.append(corr.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Correlation node failure (isolated): %s", e)
            errors.append({
                "node_name": "correlation",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })

        return {
            "correlations": correlations,
            "errors": errors,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Node 5 (Phase 5.3): Historical incident context                     #
    # ------------------------------------------------------------------ #
    def historical_context_node(state: InvestigationState) -> dict[str, Any]:
        """Node 5 (5.3): Enrich state with historical incident context (read-only).

        This node operates without a DB session — the investigation service
        pre-fetches historical matches and injects them via initial_state
        historical_context field.  If historical_context is empty (e.g. fresh
        database), reasoning continues without it.
        """
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("historical_context")
        metadata["nodes_executed"] = nodes_executed

        historical_matches = state.get("historical_context") or []
        note = build_historical_context_note(historical_matches)
        if note:
            metadata["historical_context_note"] = note
            metadata["historical_match_count"] = len(historical_matches)
        else:
            metadata["historical_match_count"] = 0

        return {"metadata": metadata}

    # ------------------------------------------------------------------ #
    # Node 6 (Phase 5.3): Competing hypotheses generation                 #
    # ------------------------------------------------------------------ #
    def hypotheses_node(state: InvestigationState) -> dict[str, Any]:
        """Node 6 (5.3): Formulate competing evidence-grounded hypotheses.

        Generates multiple ranked hypotheses (one per plausible causal domain)
        rather than a single hypothesis, then enriches them with historical context.
        """
        evidence = state.get("evidence", {})
        findings = state.get("findings", [])
        valid_ids = extract_valid_evidence_ids(evidence)
        historical_matches = state.get("historical_context") or []

        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("hypotheses")
        metadata["nodes_executed"] = nodes_executed

        hypotheses_data: list[dict[str, Any]] = []
        errors = list(state.get("errors", []))

        # --- Optional AI path (non-mock provider) ---
        if provider is not None and provider.provider_name != "mock":
            try:
                hypothesis = provider.generate_structured(
                    AIHypothesis,
                    prompt=(
                        f"Synthesize the following investigator findings and telemetry "
                        f"into the leading hypothesis:\n"
                        f"Findings: {findings}\n"
                        f"Evidence: {evidence}"
                    ),
                    system_message=(
                        "You are TRACEIQ Root Cause Investigator. "
                        "Strictly reference real evidence IDs."
                    ),
                )
                validate_hypothesis_references(hypothesis, valid_ids)
                hypotheses_data.append(hypothesis.model_dump(mode="json"))
            except Exception as e:
                errors.append({
                    "node_name": "hypotheses",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "recovered": True,
                })
                return {"errors": errors, "metadata": metadata}

        # --- Deterministic competing hypothesis generation ---
        if not hypotheses_data:
            hypotheses_data = _build_competing_hypotheses(findings, evidence, valid_ids)

        # Enrich with historical context (metadata annotation only — no evidence ID pollution)
        if historical_matches:
            hypotheses_data = enrich_hypotheses_with_historical_context(
                hypotheses_data, historical_matches
            )

        return {
            "hypotheses": hypotheses_data,
            "errors": errors,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Node 7 (Phase 5.3): Adversarial Challenge Agent                     #
    # ------------------------------------------------------------------ #
    def challenge_node(state: InvestigationState) -> dict[str, Any]:
        """Node 7 (5.3): Adversarially challenge the leading hypothesis."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("challenge")
        metadata["nodes_executed"] = nodes_executed

        hypotheses = state.get("hypotheses", [])
        correlations = state.get("correlations", [])
        evidence = state.get("evidence", {})
        errors = list(state.get("errors", []))

        if not hypotheses:
            logger.warning("Challenge node: no hypotheses to challenge.")
            return {"metadata": metadata}

        # Challenge the leading hypothesis (ranked first in the list)
        leading_hyp_data = hypotheses[0]
        # Only use correlations that conform to our Phase 5.3 CorrelationFinding schema
        # (identifiable by the 'correlation_id' field — old evidence-format items use 'id')
        corr_data = None
        for c in correlations:
            if isinstance(c, dict) and "correlation_id" in c:
                corr_data = c
                break

        try:
            leading_hyp = AIHypothesis.model_validate(leading_hyp_data)
            corr = CorrelationFinding.model_validate(corr_data) if corr_data else None

            challenge_result = challenge_hypothesis(
                hypothesis=leading_hyp,
                correlation=corr,
                evidence=evidence,
                provider=provider,
            )
            return {
                "challenge": challenge_result.model_dump(mode="json"),
                "metadata": metadata,
            }
        except Exception as e:
            logger.warning("Challenge node failure (isolated): %s", e)
            errors.append({
                "node_name": "challenge",
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovered": True,
            })
            return {
                "errors": errors,
                "metadata": metadata,
            }

    # ------------------------------------------------------------------ #
    # Node 8: Evaluator (finalize telemetry)                              #
    # ------------------------------------------------------------------ #
    def evaluator_node(state: InvestigationState) -> dict[str, Any]:
        """Node 8: Finalize execution telemetry."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("evaluator")
        metadata["nodes_executed"] = nodes_executed
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "metadata": metadata,
        }

    # ------------------------------------------------------------------ #
    # Graph wiring                                                         #
    # ------------------------------------------------------------------ #
    workflow = StateGraph(InvestigationState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("investigate_deployment", investigate_deployment_node)
    workflow.add_node("investigate_database", investigate_database_node)
    workflow.add_node("investigate_dependency", investigate_dependency_node)
    workflow.add_node("investigate_application", investigate_application_node)
    workflow.add_node("collect_findings", collect_findings_node)
    workflow.add_node("correlation", correlation_node)
    workflow.add_node("historical_context", historical_context_node)
    workflow.add_node("hypotheses", hypotheses_node)
    workflow.add_node("challenge", challenge_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "investigate_deployment")
    workflow.add_edge("investigate_deployment", "investigate_database")
    workflow.add_edge("investigate_database", "investigate_dependency")
    workflow.add_edge("investigate_dependency", "investigate_application")
    workflow.add_edge("investigate_application", "collect_findings")
    workflow.add_edge("collect_findings", "correlation")
    workflow.add_edge("correlation", "historical_context")
    workflow.add_edge("historical_context", "hypotheses")
    workflow.add_edge("hypotheses", "challenge")
    workflow.add_edge("challenge", "evaluator")
    workflow.add_edge("evaluator", END)

    return workflow.compile()


# ------------------------------------------------------------------ #
# Deterministic competing hypothesis builder (Phase 5.3)             #
# ------------------------------------------------------------------ #
def _build_competing_hypotheses(
    findings: list[dict[str, Any]],
    evidence: dict[str, Any],
    valid_ids: set[str],
) -> list[dict[str, Any]]:
    """Generate multiple ranked, competing hypotheses from domain findings.

    Each hypothesis corresponds to a distinct causal domain observed in the
    evidence.  Hypotheses are ranked by evidence strength (strongest first).
    All evidence IDs are validated before inclusion.
    """
    hypotheses: list[dict[str, Any]] = []

    ev_list = evidence.get("evidence", [])
    sup_ids = [
        str(e["id"]) for e in ev_list
        if e.get("strength") in {"strongly_supported", "supported"} and str(e.get("id")) in valid_ids
    ]
    con_ids = [
        str(e["id"]) for e in ev_list
        if e.get("contradicts") and str(e.get("id")) in valid_ids
    ]

    timeline = evidence.get("timeline_findings", [])
    has_deployment = any(t.get("event_type") == "deployment" for t in timeline)
    has_config = any(t.get("event_type") == "configuration" for t in timeline)
    has_dependency = any(t.get("event_type") == "dependency" for t in timeline)

    metric_findings = evidence.get("metric_findings", [])
    db_anomalies = [
        m for m in metric_findings
        if m.get("anomaly") and (
            "db" in str(m.get("service", "")).lower()
            or "connection" in str(m.get("metric", "")).lower()
            or "query" in str(m.get("metric", "")).lower()
        )
    ]
    dep_anomalies = [
        m for m in metric_findings
        if m.get("anomaly") and (
            "gateway_timeout" in str(m.get("metric", "")).lower()
            or "egress" in str(m.get("metric", "")).lower()
            or "third_party" in str(m.get("service", "")).lower()
        )
    ]

    # Classify domain findings by investigator type
    finding_by_type: dict[str, dict[str, Any]] = {}
    for f in findings:
        inv_type = f.get("investigator_type") or f.get("domain") or ""
        if inv_type:
            finding_by_type[inv_type] = f

    h_idx = 1

    def _finding_strength(inv_type: str) -> str:
        f = finding_by_type.get(inv_type, {})
        return f.get("strength", "inconclusive")

    # ----- Hypothesis 1: Deployment/Config regression -----
    if has_deployment or has_config:
        dep_strength = _finding_strength("deployment")
        if dep_strength in ("strongly_supported", "supported"):
            h_strength = dep_strength
        elif has_deployment and sup_ids:
            h_strength = "supported"
        else:
            h_strength = "weakly_supported"

        if has_deployment:
            title = "Application regression introduced by recent deployment"
            explanation = (
                "A deployment event was logged immediately before the incident window. "
                "Metric and log telemetry shows degradation aligning with the release timestamp."
            )
        else:
            title = "Configuration parameter regression"
            explanation = (
                "A configuration change was applied during or before the incident window. "
                "Modified settings may have caused service degradation."
            )

        h = AIHypothesis(
            id=f"hyp-{h_idx:02d}",
            title=title,
            explanation=explanation,
            supporting_evidence_ids=sup_ids[:5],
            contradicting_evidence_ids=con_ids[:3],
            missing_evidence=[
                "Deployment diff / rollback validation",
                "Canary vs stable error rate comparison",
            ],
            reasoning_summary=(
                f"Deployment investigator strength: {dep_strength}. "
                f"{len(sup_ids)} supporting evidence IDs, {len(con_ids)} contradicting IDs. "
                "Temporal correlation with change event."
            ),
            strength=h_strength,  # type: ignore[arg-type]
        )
        validate_hypothesis_references(h, valid_ids)
        hypotheses.append(h.model_dump(mode="json"))
        h_idx += 1

    # ----- Hypothesis 2: Database degradation -----
    if db_anomalies or "database" in finding_by_type:
        db_strength = _finding_strength("database")
        if db_strength in ("strongly_supported", "supported"):
            h_strength_db = db_strength
        elif db_anomalies:
            h_strength_db = "supported"
        else:
            h_strength_db = "weakly_supported"

        h_db = AIHypothesis(
            id=f"hyp-{h_idx:02d}",
            title="Database connection pool exhaustion or query degradation",
            explanation=(
                f"Database telemetry shows {len(db_anomalies)} metric anomaly(ies). "
                "Connection pool saturation or slow queries may be cascading to dependent services."
            ),
            supporting_evidence_ids=sup_ids[:4],
            contradicting_evidence_ids=con_ids[:2],
            missing_evidence=[
                "Database slow query log",
                "Connection pool peak utilisation chart",
            ],
            reasoning_summary=(
                f"Database investigator strength: {db_strength}. "
                f"{len(db_anomalies)} database metric anomalies detected."
            ),
            strength=h_strength_db,  # type: ignore[arg-type]
        )
        validate_hypothesis_references(h_db, valid_ids)
        hypotheses.append(h_db.model_dump(mode="json"))
        h_idx += 1

    # ----- Hypothesis 3: External dependency failure -----
    if has_dependency or dep_anomalies:
        dep_strength = _finding_strength("dependency")
        if dep_strength in ("strongly_supported", "supported"):
            h_strength_dep = dep_strength
        elif dep_anomalies:
            h_strength_dep = "supported"
        else:
            h_strength_dep = "weakly_supported"

        h_dep = AIHypothesis(
            id=f"hyp-{h_idx:02d}",
            title="External dependency degradation or timeout cascade",
            explanation=(
                f"Third-party service degradation events in timeline. "
                f"{len(dep_anomalies)} egress/gateway timeout metric anomalies observed."
            ),
            supporting_evidence_ids=sup_ids[:3],
            contradicting_evidence_ids=con_ids[:2],
            missing_evidence=[
                "Third-party provider status page",
                "Circuit breaker trip logs",
            ],
            reasoning_summary=(
                f"Dependency investigator strength: {dep_strength}. "
                f"{len(dep_anomalies)} dependency metric anomalies."
            ),
            strength=h_strength_dep,  # type: ignore[arg-type]
        )
        validate_hypothesis_references(h_dep, valid_ids)
        hypotheses.append(h_dep.model_dump(mode="json"))
        h_idx += 1

    # ----- Fallback: at least one hypothesis must exist -----
    if not hypotheses:
        h_fallback = AIHypothesis(
            id="hyp-01",
            title="Undetermined root cause — investigation inconclusive",
            explanation=(
                "Insufficient multi-domain evidence to form a specific hypothesis. "
                "Continue investigation with expanded telemetry scope."
            ),
            supporting_evidence_ids=sup_ids[:3],
            contradicting_evidence_ids=con_ids[:1],
            missing_evidence=["Additional metric telemetry", "Expanded log coverage"],
            reasoning_summary=(
                f"Synthesized from {len(findings)} domain findings. "
                "No dominant causal signal identified."
            ),
            strength="inconclusive",
        )
        validate_hypothesis_references(h_fallback, valid_ids)
        hypotheses.append(h_fallback.model_dump(mode="json"))

    # Sort: strongly_supported first, then supported, then weaker
    _strength_order = {
        "strongly_supported": 0,
        "supported": 1,
        "weakly_supported": 2,
        "inconclusive": 3,
        "rejected": 4,
    }
    hypotheses.sort(key=lambda h: _strength_order.get(h.get("strength", "inconclusive"), 5))

    return hypotheses
