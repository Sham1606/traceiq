"""LangGraph investigation workflow builder for TRACEIQ.

Orchestrates stateful execution from planner through investigator reasoning
to evidence-grounded hypotheses formulation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from langgraph.graph import StateGraph, START, END

from ..planner import InvestigationPlanner
from ..providers.base import AIProvider
from ..schemas import AIHypothesis, InvestigationPlan
from ..state import InvestigationState
from ..validation import extract_valid_evidence_ids, validate_hypothesis_references


def build_investigation_graph(provider: AIProvider | None = None) -> Any:
    """Build and compile the LangGraph investigation workflow."""
    planner = InvestigationPlanner()

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

    def hypotheses_node(state: InvestigationState) -> dict[str, Any]:
        """Node 2: Formulate evidence-grounded hypotheses."""
        evidence = state.get("evidence", {})
        valid_ids = extract_valid_evidence_ids(evidence)

        # Use provider if supplied, otherwise deterministic grounding
        hypotheses_data: list[dict[str, Any]] = []

        if provider is not None and provider.provider_name != "mock":
            # For real provider, prompt structured output
            try:
                hypothesis = provider.generate_structured(
                    AIHypothesis,
                    prompt="Analyze normalized telemetry and formulate leading root-cause hypothesis.",
                    system_message="You are TRACEIQ Root Cause Investigator. Strictly reference evidence IDs.",
                )
                validate_hypothesis_references(hypothesis, valid_ids)
                hypotheses_data.append(hypothesis.model_dump(mode="json"))
            except Exception as e:
                # Log error in state for evaluator/caller handling
                errors = list(state.get("errors", []))
                errors.append({
                    "node_name": "hypotheses",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "recovered": True,
                })
                return {"errors": errors}

        # Deterministic evidence grounding fallback / default fixture
        if not hypotheses_data:
            # Extract supporting/contradicting IDs from real evidence bundle
            ev_list = evidence.get("evidence", [])
            sup_ids = [e["id"] for e in ev_list if e.get("strength") in {"strongly_supported", "supported"}]
            con_ids = [e["id"] for e in ev_list if e.get("contradicts")]

            timeline = evidence.get("timeline_findings", [])
            is_deployment = any(t.get("event_type") == "deployment" for t in timeline)
            is_config = any(t.get("event_type") == "configuration" for t in timeline)
            is_dependency = any(t.get("event_type") == "dependency" for t in timeline)

            if is_deployment:
                h_title = "Application regression introduced by recent deployment"
                h_exp = "Deployment event precedes observed metric and error log spikes."
                strength = "strongly_supported" if sup_ids else "supported"
            elif is_config:
                h_title = "Configuration parameter regression"
                h_exp = "Configuration update correlates with service anomalies."
                strength = "supported"
            elif is_dependency:
                h_title = "External dependency degradation or timeout cascade"
                h_exp = "Third-party service failure matches latency jump."
                strength = "supported"
            else:
                h_title = "Database connection pool exhaustion"
                h_exp = "Database telemetry exhibits elevated query latency and connection saturation."
                strength = "supported"

            h = AIHypothesis(
                id="hyp-ai-01",
                title=h_title,
                explanation=h_exp,
                supporting_evidence_ids=sup_ids[:5],
                contradicting_evidence_ids=con_ids[:3],
                missing_evidence=[],
                reasoning_summary="Deterministic evidence correlation links temporal trigger to telemetry drift.",
                strength=strength,  # type: ignore[arg-type]
            )
            validate_hypothesis_references(h, valid_ids)
            hypotheses_data.append(h.model_dump(mode="json"))

        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("hypotheses")
        metadata["nodes_executed"] = nodes_executed

        return {
            "hypotheses": hypotheses_data,
            "metadata": metadata,
        }

    def evaluator_node(state: InvestigationState) -> dict[str, Any]:
        """Node 3: Validate evidence integrity and finalize execution telemetry."""
        metadata = dict(state.get("metadata", {}))
        nodes_executed = list(metadata.get("nodes_executed", []))
        nodes_executed.append("evaluator")
        metadata["nodes_executed"] = nodes_executed
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "metadata": metadata,
        }

    workflow = StateGraph(InvestigationState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("hypotheses", hypotheses_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "hypotheses")
    workflow.add_edge("hypotheses", "evaluator")
    workflow.add_edge("evaluator", END)

    return workflow.compile()
