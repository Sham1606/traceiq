"""Structured schemas for TRACEIQ AI investigation contracts.

All AI-derived outputs are validated against these Pydantic schemas.
Arbitrary confidence percentages are forbidden; explainable strength labels are mandatory.
Evidence references are required for all RCA and finding claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

EvidenceStrengthLabel = Literal[
    "strongly_supported",
    "supported",
    "inconclusive",
    "weakly_supported",
    "rejected",
]


class InvestigationPlanStep(BaseModel):
    """A discrete investigation step planned for a domain investigator."""
    model_config = ConfigDict(extra="forbid")

    step_id: str
    investigator_type: Literal[
        "application",
        "database",
        "deployment",
        "dependency",
        "correlation",
        "hypotheses",
    ]
    reason: str
    priority: int = Field(default=1, ge=1, le=10)
    dependencies: list[str] = Field(default_factory=list)
    status: Literal["pending", "running", "completed", "skipped", "failed"] = "pending"


class InvestigationPlan(BaseModel):
    """Structured plan specifying investigator sequencing and telemetry priorities."""
    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    steps: list[InvestigationPlanStep] = Field(default_factory=list)
    status: Literal["planned", "in_progress", "completed", "failed"] = "planned"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigatorFinding(BaseModel):
    """Domain-specific findings formulated by a specialized investigator."""
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    investigator_type: Literal[
        "application",
        "database",
        "deployment",
        "dependency",
        "correlation",
    ]
    domain: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    anomalies_detected: list[str] = Field(default_factory=list)
    confidence_label: EvidenceStrengthLabel
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIHypothesis(BaseModel):
    """Structured hypothesis candidate formulated by AI reasoning over evidence."""
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    explanation: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str
    strength: EvidenceStrengthLabel


class ChallengeResult(BaseModel):
    """Adversarial stress-test result challenging the leading hypothesis."""
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    status: Literal["supported", "rejected", "inconclusive"]
    challenge_rationale: str
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    independent_evidence_ids: list[str] = Field(default_factory=list)
    challenger_agent: str = "ChallengeAgent"


class RecoveryRecommendation(BaseModel):
    """Recommended recovery action formulated from verified root cause."""
    model_config = ConfigDict(extra="forbid")

    action: str
    target: str
    rationale: str
    expected_impact: str
    requires_human_approval: bool = True
    risk_level: Literal["low", "medium", "high"] = "medium"
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class PostmortemDraft(BaseModel):
    """Structured postmortem generated following investigation and recovery."""
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    impact_duration_minutes: float | None = None
    root_cause_analysis: str
    causal_sequence: list[str] = Field(default_factory=list)
    remediation_summary: str
    action_items: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)


class AIExecutionError(BaseModel):
    """Structured execution error record within the AI investigation."""
    model_config = ConfigDict(extra="forbid")

    node_name: str
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recovered: bool = False


class InvestigationMetadata(BaseModel):
    """Metadata tracking AI execution telemetry and governance."""
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    nodes_executed: list[str] = Field(default_factory=list)
    deterministic_fallback: bool = False
