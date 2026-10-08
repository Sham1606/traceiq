"""SQLAlchemy ORM models for TRACEIQ backend persistence.

All JSON-heavy fields use Text columns storing serialised JSON.
No ground-truth fields are stored here; ground truth stays in test-only data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class IncidentRow(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    affected_services_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    investigations: Mapped[list["InvestigationRow"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list["AuditEntryRow"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )

    @property
    def affected_services(self) -> list[str]:
        return json.loads(self.affected_services_json)

    @affected_services.setter
    def affected_services(self, value: list[str]) -> None:
        self.affected_services_json = json.dumps(value)


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------

class InvestigationRow(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    incident_id: Mapped[str] = mapped_column(Text, ForeignKey("incidents.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    # Evidence bundle stored as JSON text — never includes ground truth
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI-generated hypotheses stored as JSON text
    hypotheses_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Challenge result stored as JSON text
    challenge_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Postmortem draft stored as JSON text
    postmortem_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    incident: Mapped["IncidentRow"] = relationship(back_populates="investigations")
    recovery_actions: Mapped[list["RecoveryActionRow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )

    @property
    def evidence(self) -> dict | None:
        return json.loads(self.evidence_json) if self.evidence_json else None

    @evidence.setter
    def evidence(self, value: dict | None) -> None:
        self.evidence_json = json.dumps(value) if value is not None else None

    @property
    def hypotheses(self) -> list[dict] | None:
        return json.loads(self.hypotheses_json) if self.hypotheses_json else None

    @hypotheses.setter
    def hypotheses(self, value: list[dict] | None) -> None:
        self.hypotheses_json = json.dumps(value) if value is not None else None

    @property
    def challenge(self) -> dict | None:
        return json.loads(self.challenge_json) if self.challenge_json else None

    @challenge.setter
    def challenge(self, value: dict | None) -> None:
        self.challenge_json = json.dumps(value) if value is not None else None

    @property
    def postmortem(self) -> dict | None:
        return json.loads(self.postmortem_json) if self.postmortem_json else None

    @postmortem.setter
    def postmortem(self, value: dict | None) -> None:
        self.postmortem_json = json.dumps(value) if value is not None else None


# ---------------------------------------------------------------------------
# Recovery Actions
# ---------------------------------------------------------------------------

class RecoveryActionRow(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(Text, ForeignKey("investigations.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    requires_human_approval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approval_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    simulated_result: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Detail JSON holds Phase 5.4 fields: action_type, blast_radius, risk_level, execution_simulation, etc.
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    investigation: Mapped["InvestigationRow"] = relationship(back_populates="recovery_actions")

    @property
    def detail(self) -> dict | None:
        return json.loads(self.detail_json) if self.detail_json else None

    @detail.setter
    def detail(self, value: dict | None) -> None:
        self.detail_json = json.dumps(value) if value is not None else None


# ---------------------------------------------------------------------------
# Historical Memory
# ---------------------------------------------------------------------------

class IncidentMemoryRow(Base):
    __tablename__ = "incident_memory"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    # Deterministic fingerprint for similarity matching
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_category: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON list of evidence summary strings
    evidence_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    recovery_action: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    @property
    def evidence_summary(self) -> list[str]:
        return json.loads(self.evidence_summary_json)

    @evidence_summary.setter
    def evidence_summary(self, value: list[str]) -> None:
        self.evidence_summary_json = json.dumps(value)


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditEntryRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(Text, ForeignKey("incidents.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    incident: Mapped["IncidentRow"] = relationship(back_populates="audit_entries")

    @property
    def detail(self) -> dict:
        return json.loads(self.detail_json)

    @detail.setter
    def detail(self, value: dict) -> None:
        self.detail_json = json.dumps(value)
