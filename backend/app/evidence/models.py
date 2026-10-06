from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MetricFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    service: str
    metric: str
    baseline_mean: float
    incident_mean: float
    delta: float
    delta_ratio: float | None = None
    direction: str
    anomaly: bool
    source_ids: list[str] = Field(default_factory=list)
    summary: str


class TimelineFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    event_type: str
    event_id: str
    timestamp: datetime
    related_event_ids: list[str] = Field(default_factory=list)
    ordering: str
    summary: str


class LogFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    service: str
    event_type: str
    count: int
    error_or_warn_count: int
    source_ids: list[str] = Field(default_factory=list)
    summary: str


class CorrelationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    category: str
    source_ids: list[str]
    services: list[str]
    summary: str
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    incident_id: str
    metric_findings: list[MetricFinding] = Field(default_factory=list)
    timeline_findings: list[TimelineFinding] = Field(default_factory=list)
    log_findings: list[LogFinding] = Field(default_factory=list)
    correlation_findings: list[CorrelationFinding] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
