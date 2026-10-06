"""Internal validated schemas for hypothesis output.

These are separate from the API schemas to allow the AI layer to validate
its own output before it is persisted or returned to callers.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceStrengthLabel = Literal[
    "strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"
]


class HypothesisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    strength: EvidenceStrengthLabel
