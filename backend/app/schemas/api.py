"""Pydantic API schemas for TRACEIQ.

These are the request/response bodies for the HTTP API.
They are separate from the ORM models and from the data-layer schemas in traceiq_data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok", "degraded"]
    version: str
    db: Literal["ok", "error"]


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    severity: Literal["sev1", "sev2", "sev3", "sev4"]
    started_at: datetime
    detected_at: datetime
    recovered_at: datetime
    affected_services: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=2000)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    scenario_id: str
    title: str
    status: str
    severity: str
    started_at: datetime
    detected_at: datetime
    recovered_at: datetime
    affected_services: list[str]
    description: str
    created_at: datetime


class IncidentList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int
    items: list[IncidentResponse]


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------

class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    incident_id: str
    status: str
    evidence: dict | None = None
    hypotheses: list[dict] | None = None
    challenge: dict | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Hypotheses
# ---------------------------------------------------------------------------

class HypothesisItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    explanation: str
    evidence_ids: list[str]
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    strength: str


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

class RecoveryActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., min_length=1, max_length=500)
    target: str = Field(..., min_length=1, max_length=200)
    rationale: str = Field(..., min_length=1, max_length=2000)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved_by: str = Field(..., min_length=1, max_length=100)
    approved: bool


class RecoveryActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    investigation_id: str
    action: str
    target: str
    rationale: str
    requires_human_approval: bool
    approval_status: str
    approved_by: str | None
    approved_at: datetime | None
    simulated_result: str
    outcome: str | None
    created_at: datetime


class SimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recovery_action_id: str
    simulated_result: Literal["safe", "unsafe", "partial"]
    notes: str


# ---------------------------------------------------------------------------
# Historical Memory
# ---------------------------------------------------------------------------

class IncidentMemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fingerprint: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=255)
    root_cause_category: str = Field(..., min_length=1, max_length=100)
    evidence_summary: list[str] = Field(default_factory=list)
    recovery_action: str = Field(..., min_length=1, max_length=500)
    recovery_outcome: str = Field(..., min_length=1, max_length=500)
    scenario_id: str
    incident_id: str


class IncidentMemoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    fingerprint: str
    title: str
    root_cause_category: str
    evidence_summary: list[str]
    recovery_action: str
    recovery_outcome: str
    scenario_id: str
    incident_id: str
    created_at: datetime


class MemoryMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory: IncidentMemoryResponse
    shared_fingerprint_tokens: list[str]
    match_note: str


class MemorySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_fingerprint: str
    matches: list[MemoryMatch]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    incident_id: str
    action: str
    actor: str
    detail: dict
    created_at: datetime
