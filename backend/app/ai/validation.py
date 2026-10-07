"""Validation utilities for structured AI outputs and evidence references.

Enforces that:
1. All AI hypotheses and findings strictly reference evidence IDs established
   by the deterministic evidence engine.
2. Hallucinated evidence IDs or unknown references are rejected.
3. Strength ratings strictly match allowed explainable labels.
"""
from __future__ import annotations

from typing import Any
from .schemas import AIHypothesis, InvestigatorFinding


class AIValidationError(Exception):
    """Raised when structured AI output violates semantic or evidence reference contracts."""
    pass


def extract_valid_evidence_ids(evidence_data: dict[str, Any]) -> set[str]:
    """Extract all legitimate evidence IDs present in a normalized evidence bundle."""
    valid_ids: set[str] = set()

    # Evidence items
    for item in evidence_data.get("evidence", []):
        if isinstance(item, dict) and "id" in item:
            valid_ids.add(str(item["id"]))

    # Metric findings
    for item in evidence_data.get("metric_findings", []):
        if isinstance(item, dict) and "id" in item:
            valid_ids.add(str(item["id"]))

    # Timeline findings
    for item in evidence_data.get("timeline_findings", []):
        if isinstance(item, dict):
            if "id" in item:
                valid_ids.add(str(item["id"]))
            if "event_id" in item:
                valid_ids.add(str(item["event_id"]))

    # Log findings
    for item in evidence_data.get("log_findings", []):
        if isinstance(item, dict) and "id" in item:
            valid_ids.add(str(item["id"]))

    # Correlation findings
    for item in evidence_data.get("correlation_findings", []):
        if isinstance(item, dict) and "id" in item:
            valid_ids.add(str(item["id"]))

    return valid_ids


def validate_evidence_ids(
    evidence_ids: list[str],
    valid_ids: set[str],
    field_name: str = "evidence_ids",
) -> None:
    """Ensure that all provided evidence IDs actually exist in the evidence bundle."""
    invalid_ids = [eid for eid in evidence_ids if eid not in valid_ids]
    if invalid_ids:
        raise AIValidationError(
            f"Invalid or hallucinated {field_name} detected: {invalid_ids}. "
            "AI agents must only reference evidence IDs produced by the deterministic engine."
        )


def validate_hypothesis_references(hypothesis: AIHypothesis, valid_ids: set[str]) -> None:
    """Validate that all evidence IDs in an AIHypothesis are valid."""
    validate_evidence_ids(
        hypothesis.supporting_evidence_ids,
        valid_ids,
        field_name=f"hypothesis({hypothesis.id}).supporting_evidence_ids",
    )
    validate_evidence_ids(
        hypothesis.contradicting_evidence_ids,
        valid_ids,
        field_name=f"hypothesis({hypothesis.id}).contradicting_evidence_ids",
    )


def validate_finding_references(finding: InvestigatorFinding, valid_ids: set[str]) -> None:
    """Validate that all evidence IDs in an InvestigatorFinding are valid."""
    validate_evidence_ids(
        finding.evidence_ids,
        valid_ids,
        field_name=f"finding({finding.finding_id}).evidence_ids",
    )
    if finding.supporting_evidence_ids:
        validate_evidence_ids(
            finding.supporting_evidence_ids,
            valid_ids,
            field_name=f"finding({finding.finding_id}).supporting_evidence_ids",
        )
    if finding.contradicting_evidence_ids:
        validate_evidence_ids(
            finding.contradicting_evidence_ids,
            valid_ids,
            field_name=f"finding({finding.finding_id}).contradicting_evidence_ids",
        )


def validate_plan(
    plan: Any,
    evidence: dict[str, Any] | None = None,
) -> None:
    """Validate structured InvestigationPlan integrity, dependencies, and evidence grounding."""
    from .schemas import InvestigationPlan

    if not isinstance(plan, InvestigationPlan):
        raise AIValidationError(f"Expected InvestigationPlan instance, got {type(plan).__name__}")

    allowed_types = {
        "application",
        "database",
        "deployment",
        "dependency",
        "correlation",
        "hypotheses",
    }

    seen_step_ids: set[str] = set()
    seen_investigator_types: set[str] = set()
    step_id_map: dict[str, list[str]] = {}

    for step in plan.steps:
        # Check investigator type
        if step.investigator_type not in allowed_types:
            raise AIValidationError(
                f"Unsupported investigator_type: '{step.investigator_type}'. "
                f"Must be one of {sorted(allowed_types)}."
            )

        # Check non-empty reason
        if not step.reason or not step.reason.strip():
            raise AIValidationError(f"Investigation step '{step.step_id}' must have a non-empty reason.")

        # Check priority range
        if not (1 <= step.priority <= 10):
            raise AIValidationError(
                f"Investigation step '{step.step_id}' has invalid priority {step.priority} (must be 1-10)."
            )

        # Check duplicate step_id
        if step.step_id in seen_step_ids:
            raise AIValidationError(f"Duplicate step_id detected in plan: '{step.step_id}'.")
        seen_step_ids.add(step.step_id)

        # Check duplicate investigator type
        if step.investigator_type in seen_investigator_types:
            raise AIValidationError(
                f"Duplicate investigator_type detected in plan: '{step.investigator_type}'."
            )
        seen_investigator_types.add(step.investigator_type)

        step_id_map[step.step_id] = list(step.dependencies)

    # Check dependencies existence
    for step_id, deps in step_id_map.items():
        for dep in deps:
            if dep not in seen_step_ids:
                raise AIValidationError(
                    f"Step '{step_id}' references unknown dependency step: '{dep}'."
                )

    # Check circular dependencies (DAG cycle detection)
    visited: dict[str, int] = {}  # 0: visiting, 1: visited

    def has_cycle(node: str) -> bool:
        visited[node] = 0
        for neighbor in step_id_map.get(node, []):
            if neighbor in visited:
                if visited[neighbor] == 0:
                    return True
            else:
                if has_cycle(neighbor):
                    return True
        visited[node] = 1
        return False

    for s_id in seen_step_ids:
        if s_id not in visited:
            if has_cycle(s_id):
                raise AIValidationError("Circular dependency detected in investigation plan steps.")

    # Validate evidence references in evidence_scope if specific IDs provided
    if evidence is not None:
        valid_ids = extract_valid_evidence_ids(evidence)
        for step in plan.steps:
            concrete_ids = [s for s in step.evidence_scope if s.startswith("ev-") or s.startswith("timeline-")]
            if concrete_ids:
                validate_evidence_ids(concrete_ids, valid_ids, field_name=f"step({step.step_id}).evidence_scope")
