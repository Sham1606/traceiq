"""Ground truth protection for TRACEIQ AI layer.

Ensures that hidden scenario ground truth fields are strictly forbidden
from entering AI prompts, states, or reasoning pipelines.
"""
from __future__ import annotations

from typing import Any

HIDDEN_GROUND_TRUTH_KEYS: frozenset[str] = frozenset({
    "root_cause_service",
    "contradictory_lead",
    "expected_recovery_action",
    "primary_evidence_ids",
    "ground_truth",
})


def contains_ground_truth(data: Any) -> bool:
    """Recursively check whether data contains any forbidden ground-truth fields."""
    if isinstance(data, dict):
        for key, val in data.items():
            if str(key).lower() in HIDDEN_GROUND_TRUTH_KEYS:
                return True
            if contains_ground_truth(val):
                return True
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            if contains_ground_truth(item):
                return True
    return False


def assert_no_ground_truth(data: Any) -> None:
    """Raise ValueError if hidden ground truth is detected in payload."""
    if contains_ground_truth(data):
        raise ValueError(
            "Forbidden ground truth detected in AI data payload. "
            "AI reasoning must infer conclusions from normalized evidence only."
        )


def sanitize_evidence_payload(data: Any) -> Any:
    """Recursively strip any hidden ground-truth fields from dictionaries or lists."""
    if isinstance(data, dict):
        sanitized = {}
        for key, val in data.items():
            if str(key).lower() not in HIDDEN_GROUND_TRUTH_KEYS:
                sanitized[key] = sanitize_evidence_payload(val)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_evidence_payload(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_evidence_payload(item) for item in data)
    return data
