"""Recovery and audit API router (Phase 5.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import (
    ApprovalRequest,
    AuditEntryResponse,
    IncidentMemoryResponse,
    PostmortemCreateRequest,
    PostmortemResponse,
    RecoveryActionCreate,
    RecoveryActionResponse,
)
from app.services.recovery import (
    approve_recovery_action,
    archive_incident_memory,
    create_recovery_action,
    generate_postmortem,
    get_audit_log,
    get_postmortem,
    get_recovery_action,
    list_recovery_actions,
    recommend_recovery_actions,
    record_outcome,
    simulate_blast_radius,
    simulate_recovery_action,
    simulate_recovery_execution,
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


@router.post(
    "/investigations/{investigation_id}/recommend-recovery",
    response_model=list[RecoveryActionResponse],
    status_code=201,
)
def recommend_actions(investigation_id: str, db: Session = Depends(get_db)):
    """Formulate evidence-grounded candidate recovery recommendations from validated RCA."""
    try:
        return recommend_recovery_actions(db, investigation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
    """Pre-execution safety simulation (B005 compatibility). Requires human approval."""
    try:
        result = simulate_recovery_action(db, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


@router.post("/recovery-actions/{action_id}/blast-radius")
def blast_radius(action_id: str, db: Session = Depends(get_db)):
    """Deterministic blast-radius evaluation for operator review before approval."""
    try:
        sim = simulate_blast_radius(db, action_id)
        return sim.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/recovery-actions/{action_id}/execute", response_model=RecoveryActionResponse)
def execute_simulation(action_id: str, db: Session = Depends(get_db)):
    """Execute simulated recovery on synthetic scenario telemetry. Requires human approval."""
    try:
        return simulate_recovery_execution(db, action_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/recovery-actions/{action_id}/outcome", response_model=RecoveryActionResponse)
def set_outcome(action_id: str, outcome: str, db: Session = Depends(get_db)):
    result = record_outcome(db, action_id, outcome)
    if result is None:
        raise HTTPException(status_code=404, detail="Recovery action not found")
    return result


# --- Postmortem ---

@router.post(
    "/investigations/{investigation_id}/postmortem",
    response_model=PostmortemResponse,
    status_code=201,
)
def create_postmortem(
    investigation_id: str,
    payload: PostmortemCreateRequest | None = None,
    db: Session = Depends(get_db),
):
    try:
        notes = payload.custom_notes if payload else None
        draft = generate_postmortem(db, investigation_id, custom_notes=notes)
        return PostmortemResponse.model_validate(draft.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/investigations/{investigation_id}/postmortem",
    response_model=PostmortemResponse,
)
def read_postmortem(investigation_id: str, db: Session = Depends(get_db)):
    data = get_postmortem(db, investigation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Postmortem not yet generated")
    return PostmortemResponse.model_validate(data)


# --- Incident Memory Archival ---

@router.post(
    "/investigations/{investigation_id}/archive-memory",
    response_model=IncidentMemoryResponse,
    status_code=201,
)
def archive_memory(investigation_id: str, db: Session = Depends(get_db)):
    try:
        return archive_incident_memory(db, investigation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- Audit log ---

@router.get("/incidents/{incident_id}/audit", response_model=list[AuditEntryResponse])
def get_audit(incident_id: str, db: Session = Depends(get_db)):
    return get_audit_log(db, incident_id)
