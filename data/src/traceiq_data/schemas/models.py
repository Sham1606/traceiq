from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceStrength(str, Enum):
    STRONGLY_SUPPORTED = "strongly_supported"
    SUPPORTED = "supported"
    INCONCLUSIVE = "inconclusive"
    WEAKLY_SUPPORTED = "weakly_supported"
    REJECTED = "rejected"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RECOVERED = "recovered"
    CLOSED = "closed"


class Service(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    tier: Literal["edge", "application", "data", "dependency"]
    criticality: Literal["low", "medium", "high", "critical"]
    dependencies: list[str] = Field(default_factory=list)


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    scenario_id: str
    title: str
    status: IncidentStatus
    severity: Literal["sev1", "sev2", "sev3", "sev4"]
    started_at: datetime
    detected_at: datetime
    recovered_at: datetime
    affected_services: list[str]
    description: str

    @field_validator("detected_at")
    @classmethod
    def detected_after_start(cls, value: datetime, info):
        start = info.data.get("started_at")
        if start and value < start:
            raise ValueError("detected_at must be >= started_at")
        return value


class MetricPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    timestamp: datetime
    service: str
    metric: str
    value: float
    unit: str
    source: Literal["synthetic-telemetry"] = "synthetic-telemetry"


class LogEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    timestamp: datetime
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    event_type: str
    message: str
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeploymentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    timestamp: datetime
    service: str
    version_from: str
    version_to: str
    environment: Literal["production"]
    status: Literal["success", "rollback"]
    actor: str


class ConfigurationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    timestamp: datetime
    service: str
    key: str
    previous_value: str
    new_value: str
    environment: Literal["production"]
    change_type: Literal["application", "infrastructure", "dependency"]


class DependencyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    timestamp: datetime
    service: str
    dependency: str
    latency_ms: float
    error_rate: float = Field(ge=0, le=1)
    timeout_rate: float = Field(ge=0, le=1)
    status: Literal["healthy", "degraded", "failed"]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    incident_id: str
    evidence_type: Literal["metric", "log", "deployment", "configuration", "dependency", "timeline", "historical"]
    source_id: str
    summary: str
    strength: EvidenceStrength
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    incident_id: str
    title: str
    explanation: str
    evidence_ids: list[str]
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    strength: EvidenceStrength


class RecoveryAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    incident_id: str
    action: str
    target: str
    rationale: str
    requires_human_approval: bool = True
    simulated_result: Literal["not_run", "safe", "unsafe", "partial"] = "not_run"


class HistoricalIncidentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    fingerprint: str
    title: str
    root_cause_category: str
    evidence_summary: list[str]
    recovery_action: str
    recovery_outcome: str


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    root_cause_category: Literal[
        "bad_deployment",
        "database_degradation",
        "external_dependency_failure",
        "configuration_regression",
    ]
    root_cause_service: str
    primary_evidence_ids: list[str]
    contradictory_lead: str
    expected_recovery_action: str
    expected_post_recovery_state: str


class ScenarioBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0"
    scenario_id: str
    seed: int
    incident: Incident
    services: list[Service]
    metrics: list[MetricPoint]
    logs: list[LogEvent]
    deployments: list[DeploymentEvent]
    configuration_changes: list[ConfigurationChange]
    dependencies: list[DependencyEvent]
