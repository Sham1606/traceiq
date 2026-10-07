"""Structured schemas for TRACEIQ AI investigation contracts.

All AI-derived outputs are validated against these Pydantic schemas.
Arbitrary confidence percentages are forbidden; explainable strength labels are mandatory.
Evidence references are required for all RCA and finding claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    evidence_scope: list[str] = Field(default_factory=list)
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
    title: str = Field(default="")
    reasoning: str = Field(default="")
    strength: EvidenceStrengthLabel = Field(default="supported")
    confidence_label: EvidenceStrengthLabel = Field(default="supported")
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    anomalies_detected: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_finding_fields(self) -> InvestigatorFinding:
        """Keep evidence_ids, title, and strength labels synchronized for backwards compatibility."""
        if not self.evidence_ids and self.supporting_evidence_ids:
            self.evidence_ids = list(self.supporting_evidence_ids)
        elif self.evidence_ids and not self.supporting_evidence_ids:
            self.supporting_evidence_ids = list(self.evidence_ids)

        if not self.title and self.summary:
            self.title = self.summary[:80]

        if self.strength != "supported" and self.confidence_label == "supported":
            self.confidence_label = self.strength
        elif self.confidence_label != "supported" and self.strength == "supported":
            self.strength = self.confidence_label
        return self


class CorrelationFinding(BaseModel):
    """Cross-investigator evidence correlation produced by the deterministic correlation engine.

    Every claim must be backed by validated evidence IDs.  The engine never
    receives hidden ground truth — it works only from domain-investigator findings.
    """
    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    # Domains that share corroborating evidence signals
    correlated_domains: list[str] = Field(default_factory=list)
    # Evidence IDs that appear across multiple domain findings (cross-domain signals)
    shared_evidence_ids: list[str] = Field(default_factory=list)
    # Timeline ordering of key events (human-readable labels, not raw data)
    causal_sequence: list[str] = Field(default_factory=list)
    # Domains where the temporal evidence clearly does NOT support correlation
    false_lead_domains: list[str] = Field(default_factory=list)
    # IDs of evidence that contradict or weaken the leading correlation
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    # Narrative summary produced by the correlation engine
    summary: str
    # Combined strength label derived from cross-domain signal density
    strength: EvidenceStrengthLabel = "supported"


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
