"""Shared Investigation State representation for LangGraph and AI orchestration.

Maintains typed, serializable state throughout the multi-stage AI reasoning workflow.
Strictly isolates hidden ground truth from entering the state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict
from pydantic import BaseModel, ConfigDict, Field

from .ground_truth import sanitize_evidence_payload, assert_no_ground_truth
from .schemas import (
    AIExecutionError,
    AIHypothesis,
    ChallengeResult,
    InvestigationMetadata,
    InvestigationPlan,
    InvestigatorFinding,
    PostmortemDraft,
    RecoveryRecommendation,
)


class IncidentContext(BaseModel):
    """Contextual metadata regarding the incident under investigation."""
    model_config = ConfigDict(extra="forbid")

    id: str
    scenario_id: str
    title: str
    severity: str
    started_at: datetime
    detected_at: datetime
    recovered_at: datetime
    affected_services: list[str] = Field(default_factory=list)
    description: str = ""


class InvestigationState(TypedDict, total=False):
    """LangGraph compatible state dictionary for stateful investigation workflows."""
    incident: dict[str, Any]
    evidence: dict[str, Any]
    plan: dict[str, Any] | None
    findings: list[dict[str, Any]]
    correlations: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    challenge: dict[str, Any] | None
    historical_context: list[dict[str, Any]]
    recovery: dict[str, Any] | None
    postmortem: dict[str, Any] | None
    errors: list[dict[str, Any]]
    metadata: dict[str, Any]


class InvestigationStateModel(BaseModel):
    """Pydantic model of the complete investigation state for strict validation and serialization."""
    model_config = ConfigDict(extra="ignore")

    incident: IncidentContext
    evidence: dict[str, Any] = Field(default_factory=dict)
    plan: InvestigationPlan | None = None
    findings: list[InvestigatorFinding] = Field(default_factory=list)
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[AIHypothesis] = Field(default_factory=list)
    challenge: ChallengeResult | None = None
    historical_context: list[dict[str, Any]] = Field(default_factory=list)
    recovery: RecoveryRecommendation | None = None
    postmortem: PostmortemDraft | None = None
    errors: list[AIExecutionError] = Field(default_factory=list)
    metadata: InvestigationMetadata = Field(
        default_factory=lambda: InvestigationMetadata(
            provider="mock",
            model="mock-reasoner",
            started_at=datetime.now(timezone.utc),
        )
    )


def create_initial_state(
    incident: Any,
    evidence_bundle: Any,
    provider: str = "mock",
    model: str = "mock-reasoner",
) -> InvestigationState:
    """Construct a clean, sanitized initial investigation state for LangGraph.

    Ensures that any hidden ground truth is stripped before state initialization.
    """
    # Extract incident context
    if hasattr(incident, "__dict__"):
        inc_dict = {
            "id": getattr(incident, "id"),
            "scenario_id": getattr(incident, "scenario_id"),
            "title": getattr(incident, "title"),
            "severity": getattr(incident, "severity"),
            "started_at": getattr(incident, "started_at"),
            "detected_at": getattr(incident, "detected_at"),
            "recovered_at": getattr(incident, "recovered_at"),
            "affected_services": getattr(incident, "affected_services", []),
            "description": getattr(incident, "description", ""),
        }
    elif isinstance(incident, dict):
        inc_dict = dict(incident)
        inc_dict.setdefault("description", "")
        inc_dict.setdefault("affected_services", [])
    else:
        raise ValueError(f"Unsupported incident type: {type(incident)}")

    # Extract & sanitize evidence bundle
    if hasattr(evidence_bundle, "model_dump"):
        ev_dict = evidence_bundle.model_dump(mode="json")
    elif isinstance(evidence_bundle, dict):
        ev_dict = dict(evidence_bundle)
    else:
        raise ValueError(f"Unsupported evidence_bundle type: {type(evidence_bundle)}")

    clean_evidence = sanitize_evidence_payload(ev_dict)
    assert_no_ground_truth(clean_evidence)

    meta = InvestigationMetadata(
        provider=provider,
        model=model,
        started_at=datetime.now(timezone.utc),
    )

    return InvestigationState(
        incident=inc_dict,
        evidence=clean_evidence,
        plan=None,
        findings=[],
        correlations=clean_evidence.get("correlation_findings", []),
        hypotheses=[],
        challenge=None,
        historical_context=[],
        recovery=None,
        postmortem=None,
        errors=[],
        metadata=meta.model_dump(mode="json"),
    )


def serialize_state(state: InvestigationState) -> str:
    """Serialize investigation state to JSON."""
    return json.dumps(state, default=str)


def deserialize_state(json_str: str) -> InvestigationStateModel:
    """Deserialize and validate investigation state from JSON string."""
    data = json.loads(json_str)
    return InvestigationStateModel.model_validate(data)
