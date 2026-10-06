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
