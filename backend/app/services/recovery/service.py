"""Recovery and audit service (B005).

Recovery is never autonomous:
  recommendation → evidence → approval → simulation → recorded outcome.

LLMs do not execute recovery actions. A human must approve.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.orm import AuditEntryRow, RecoveryActionRow
from app.schemas.api import (
    ApprovalRequest,
    RecoveryActionCreate,
    RecoveryActionResponse,
    SimulationResult,
    AuditEntryResponse,
)

VALID_SIMULATED_RESULTS = {"safe", "unsafe", "partial"}


def _row_to_response(row: RecoveryActionRow) -> RecoveryActionResponse:
    return RecoveryActionResponse(
        id=row.id,
        investigation_id=row.investigation_id,
        action=row.action,
        target=row.target,
        rationale=row.rationale,
        requires_human_approval=bool(row.requires_human_approval),
        approval_status=row.approval_status,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        simulated_result=row.simulated_result,
        outcome=row.outcome,
        created_at=row.created_at,
    )


def create_recovery_action(
    db: Session, investigation_id: str, payload: RecoveryActionCreate
) -> RecoveryActionResponse:
    row = RecoveryActionRow(
        id=str(uuid.uuid4()),
        investigation_id=investigation_id,
        action=payload.action,
        target=payload.target,
        rationale=payload.rationale,
        requires_human_approval=1,
        approval_status="pending",
        simulated_result="not_run",
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def approve_recovery_action(
    db: Session, action_id: str, payload: ApprovalRequest
) -> RecoveryActionResponse | None:
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        return None
    if row.approval_status != "pending":
        raise ValueError(f"Action is already in state '{row.approval_status}'.")
    row.approval_status = "approved" if payload.approved else "rejected"
    row.approved_by = payload.approved_by
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def simulate_recovery_action(
    db: Session, action_id: str
) -> RecoveryActionResponse | None:
    """Run a deterministic safety simulation before recovery is executed.

    Only approved actions can be simulated.
    """
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        return None
    if row.approval_status != "approved":
        raise ValueError("Cannot simulate a recovery action that has not been approved.")
    # Deterministic simulation: check action keywords for obviously unsafe patterns
    result = _simulate(row.action, row.target)
    row.simulated_result = result
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def record_outcome(
    db: Session, action_id: str, outcome: str
) -> RecoveryActionResponse | None:
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        return None
    row.outcome = outcome
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def get_recovery_action(db: Session, action_id: str) -> RecoveryActionResponse | None:
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        return None
    return _row_to_response(row)


def list_recovery_actions(db: Session, investigation_id: str) -> list[RecoveryActionResponse]:
    rows = (
        db.query(RecoveryActionRow)
        .filter(RecoveryActionRow.investigation_id == investigation_id)
        .order_by(RecoveryActionRow.created_at)
        .all()
    )
    return [_row_to_response(r) for r in rows]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def get_audit_log(db: Session, incident_id: str) -> list[AuditEntryResponse]:
    rows = (
        db.query(AuditEntryRow)
        .filter(AuditEntryRow.incident_id == incident_id)
        .order_by(AuditEntryRow.created_at)
        .all()
    )
    return [
        AuditEntryResponse(
            id=r.id,
            incident_id=r.incident_id,
            action=r.action,
            actor=r.actor,
            detail=r.detail,
            created_at=r.created_at,
        )
        for r in rows
    ]


def _audit(db: Session, incident_id: str, action: str, detail: dict, actor: str = "system") -> None:
    entry = AuditEntryRow(
        incident_id=incident_id,
        action=action,
        actor=actor,
        created_at=datetime.now(timezone.utc),
    )
    entry.detail = detail
    db.add(entry)
    db.commit()


# ---------------------------------------------------------------------------
# Deterministic simulation
# ---------------------------------------------------------------------------

_UNSAFE_KEYWORDS = frozenset(["delete", "drop", "purge", "rm -rf", "truncate", "destroy"])
_PARTIAL_KEYWORDS = frozenset(["restart", "scale", "migrate", "rollback"])


def _simulate(action: str, target: str) -> str:
    combined = (action + " " + target).lower()
    if any(kw in combined for kw in _UNSAFE_KEYWORDS):
        return "unsafe"
    if any(kw in combined for kw in _PARTIAL_KEYWORDS):
        return "partial"
    return "safe"
