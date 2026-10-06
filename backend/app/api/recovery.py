"""Recovery and audit API router (B005)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import (
    ApprovalRequest,
    AuditEntryResponse,
    RecoveryActionCreate,
    RecoveryActionResponse,
)
from app.services.recovery import (
    approve_recovery_action,
    create_recovery_action,
    get_audit_log,
    get_recovery_action,
    list_recovery_actions,
    record_outcome,
    simulate_recovery_action,
)

router = APIRouter(tags=["recovery"])


# --- Recovery actions under an investigation ---

@router.post(
    "/investigations/{investigation_id}/recovery-actions",
    response_model=RecoveryActionResponse,
    status_code=201,
)
def create_action(
    investigation_id: str,
    payload: RecoveryActionCreate,
    db: Session = Depends(get_db),
):
    return create_recovery_action(db, investigation_id, payload)


@router.get(
    "/investigations/{investigation_id}/recovery-actions",
    response_model=list[RecoveryActionResponse],
)
def list_actions(investigation_id: str, db: Session = Depends(get_db)):
    return list_recovery_actions(db, investigation_id)


@router.get("/recovery-actions/{action_id}", response_model=RecoveryActionResponse)
def get_action(action_id: str, db: Session = Depends(get_db)):
    result = get_recovery_action(db, action_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


@router.post("/recovery-actions/{action_id}/approve", response_model=RecoveryActionResponse)
def approve(action_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)):
    try:
        result = approve_recovery_action(db, action_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


@router.post("/recovery-actions/{action_id}/simulate", response_model=RecoveryActionResponse)
def simulate(action_id: str, db: Session = Depends(get_db)):
    try:
        result = simulate_recovery_action(db, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


@router.post("/recovery-actions/{action_id}/outcome", response_model=RecoveryActionResponse)
def set_outcome(action_id: str, outcome: str, db: Session = Depends(get_db)):
    result = record_outcome(db, action_id, outcome)
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


# --- Audit log ---

@router.get("/incidents/{incident_id}/audit", response_model=list[AuditEntryResponse])
def get_audit(incident_id: str, db: Session = Depends(get_db)):
    return get_audit_log(db, incident_id)
