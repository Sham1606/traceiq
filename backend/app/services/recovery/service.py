"""Recovery and audit service (Phase 5.4).

Recovery is never autonomous:
  RCA → Recovery Advisor → Blast-Radius Simulation → Human Approval Gate
      → Execution Simulation → Outcome → Postmortem → Historical Memory.

TRACEIQ never performs real production remediation.
LLMs do not execute recovery actions. A human operator must approve.
Deterministic simulation and safety validations are authoritative.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ai.providers.base import AIProvider
from app.ai.schemas import (
    BlastRadiusSimulation,
    PostmortemDraft,
    RecoveryActionType,
    RecoveryRecommendation,
)
from app.models.orm import AuditEntryRow, IncidentMemoryRow, IncidentRow, InvestigationRow, RecoveryActionRow
from app.schemas.api import (
    ApprovalRequest,
    AuditEntryResponse,
    IncidentMemoryCreate,
    IncidentMemoryResponse,
    RecoveryActionCreate,
    RecoveryActionResponse,
    SimulationResult,
)
from app.services.investigation.memory import store_memory
from app.services.recovery.advisor import formulate_recovery_recommendations
from app.services.recovery.blast_radius import calculate_blast_radius
from app.services.recovery.execution import execute_simulated_recovery
from app.services.recovery.postmortem import generate_postmortem_draft

VALID_SIMULATED_RESULTS = {"safe", "unsafe", "partial"}


def _row_to_response(row: RecoveryActionRow) -> RecoveryActionResponse:
    detail = row.detail or {}
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
        risk_level=detail.get("risk_level", "medium"),
        action_type=detail.get("action_type", None),
        supporting_evidence_ids=detail.get("supporting_evidence_ids", []),
        blast_radius=detail.get("blast_radius", None),
        execution_simulation=detail.get("execution_simulation", None),
        detail=detail if detail else None,
    )


def create_recovery_action(
    db: Session, investigation_id: str, payload: RecoveryActionCreate
) -> RecoveryActionResponse:
    """Create a recovery action manually or via default prompt."""
    inv = db.get(InvestigationRow, investigation_id)
    incident_id = inv.incident_id if inv else "unknown"

    # Deterministically calculate blast radius on creation
    blast = calculate_blast_radius(
        target=payload.target,
        action_type="RECOVERY_ACTION",
        action_description=payload.action,
    )

    detail_data = {
        "risk_level": blast.risk_level,
        "action_type": None,
        "supporting_evidence_ids": [],
        "blast_radius": blast.model_dump(mode="json"),
    }

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
    row.detail = detail_data
    db.add(row)
    db.commit()
    db.refresh(row)

    _audit(
        db,
        incident_id,
        "recovery_action_created",
        {"action_id": row.id, "action": row.action, "target": row.target},
    )

    return _row_to_response(row)


def recommend_recovery_actions(
    db: Session, investigation_id: str, provider: AIProvider | None = None
) -> list[RecoveryActionResponse]:
    """Run Recovery Advisor on the investigation's validated hypothesis and evidence."""
    inv = db.get(InvestigationRow, investigation_id)
    if inv is None:
        raise ValueError(f"Investigation '{investigation_id}' not found.")

    incident_id = inv.incident_id
    hypotheses = inv.hypotheses or []
    leading_hyp = hypotheses[0] if hypotheses else None
    evidence = inv.evidence or {}
    challenge = inv.challenge

    # Query historical matches if any
    historical_matches = None
    all_memories = db.query(IncidentMemoryRow).all()
    if all_memories:
        historical_matches = [
            {"title": m.title, "root_cause": m.root_cause_category, "action": m.recovery_action}
            for m in all_memories[:3]
        ]

    recs: list[RecoveryRecommendation] = formulate_recovery_recommendations(
        hypothesis=leading_hyp,
        evidence=evidence,
        challenge=challenge,
        historical_context=historical_matches,
        provider=provider,
    )

    results: list[RecoveryActionResponse] = []
    for rec in recs:
        row = RecoveryActionRow(
            id=rec.recommendation_id or str(uuid.uuid4()),
            investigation_id=investigation_id,
            action=rec.action_description or rec.action,
            target=rec.target_service or rec.target,
            rationale=rec.rationale,
            requires_human_approval=1,
            approval_status=rec.approval_status or "pending",
            simulated_result="not_run",
            created_at=datetime.now(timezone.utc),
        )
        row.detail = {
            "recommendation_id": row.id,
            "hypothesis_id": rec.hypothesis_id,
            "action_type": rec.action_type,
            "target_service": rec.target_service,
            "target_component": rec.target_component,
            "expected_effect": rec.expected_effect,
            "risk_level": rec.risk_level,
            "supporting_evidence_ids": rec.supporting_evidence_ids,
            "prerequisites": rec.prerequisites,
            "rollback_plan": rec.rollback_plan,
            "blast_radius": rec.estimated_blast_radius,
            "simulation_status": rec.simulation_status,
        }
        db.add(row)
        db.commit()
        db.refresh(row)

        _audit(
            db,
            incident_id,
            "recovery_recommendation_created",
            {
                "recommendation_id": row.id,
                "action_type": rec.action_type,
                "target": row.target,
                "hypothesis_id": rec.hypothesis_id,
                "risk_level": rec.risk_level,
            },
        )
        results.append(_row_to_response(row))

    return results


def approve_recovery_action(
    db: Session, action_id: str, payload: ApprovalRequest
) -> RecoveryActionResponse | None:
    """Enforce the mandatory human approval gate for a recovery action."""
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

    inv = db.get(InvestigationRow, row.investigation_id)
    incident_id = inv.incident_id if inv else "unknown"
    event_name = "recovery_approved" if payload.approved else "recovery_rejected"
    _audit(
        db,
        incident_id,
        event_name,
        {
            "action_id": row.id,
            "approved_by": payload.approved_by,
            "status": row.approval_status,
        },
        actor=payload.approved_by,
    )

    return _row_to_response(row)


def simulate_recovery_action(
    db: Session, action_id: str
) -> RecoveryActionResponse | None:
    """Run a deterministic safety simulation before recovery is executed.

    Only approved actions can be simulated (B005 compatibility).
    """
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        return None
    if row.approval_status != "approved":
        raise ValueError("Cannot simulate a recovery action that has not been approved.")

    # Legacy deterministic keyword simulation
    result = _simulate(row.action, row.target)
    row.simulated_result = result

    # Also compute full Phase 5.4 blast radius if not yet computed
    detail = dict(row.detail or {})
    blast = calculate_blast_radius(
        target=row.target,
        action_type=detail.get("action_type") or "RECOVERY_ACTION",
        action_description=row.action,
        recommendation_id=row.id,
    )
    detail["blast_radius"] = blast.model_dump(mode="json")
    detail["risk_level"] = blast.risk_level
    row.detail = detail

    db.commit()
    db.refresh(row)

    inv = db.get(InvestigationRow, row.investigation_id)
    incident_id = inv.incident_id if inv else "unknown"
    _audit(
        db,
        incident_id,
        "recovery_simulated",
        {"action_id": row.id, "simulated_result": result, "status": blast.status},
    )

    return _row_to_response(row)


def simulate_blast_radius(
    db: Session, action_id: str
) -> BlastRadiusSimulation:
    """Run pre-approval deterministic blast-radius evaluation."""
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        raise ValueError(f"Recovery action '{action_id}' not found.")

    detail = dict(row.detail or {})
    blast = calculate_blast_radius(
        target=row.target,
        action_type=detail.get("action_type") or "RECOVERY_ACTION",
        action_description=row.action,
        recommendation_id=row.id,
    )

    detail["blast_radius"] = blast.model_dump(mode="json")
    detail["risk_level"] = blast.risk_level
    row.detail = detail
    db.commit()
    db.refresh(row)

    inv = db.get(InvestigationRow, row.investigation_id)
    incident_id = inv.incident_id if inv else "unknown"
    _audit(
        db,
        incident_id,
        "blast_radius_simulated",
        {
            "action_id": row.id,
            "status": blast.status,
            "risk_level": blast.risk_level,
            "directly_affected": blast.directly_affected,
        },
    )

    return blast


def simulate_recovery_execution(
    db: Session, action_id: str
) -> RecoveryActionResponse:
    """Run deterministic execution simulation on an approved recovery action.

    Mandatory human approval gate is enforced.
    Simulates telemetry shift and records outcome.
    """
    row = db.get(RecoveryActionRow, action_id)
    if row is None:
        raise ValueError(f"Recovery action '{action_id}' not found.")

    detail = dict(row.detail or {})
    exec_sim = execute_simulated_recovery(
        action=row.action,
        target=row.target,
        action_type=detail.get("action_type"),
        approval_status=row.approval_status,
        recommendation_id=row.id,
    )

    row.outcome = exec_sim.status
    if row.simulated_result == "not_run":
        row.simulated_result = "safe" if exec_sim.status == "SUCCESS" else "partial"

    detail["execution_simulation"] = exec_sim.model_dump(mode="json")
    row.detail = detail
    db.commit()
    db.refresh(row)

    inv = db.get(InvestigationRow, row.investigation_id)
    incident_id = inv.incident_id if inv else "unknown"
    _audit(
        db,
        incident_id,
        "recovery_execution_simulated",
        {
            "action_id": row.id,
            "execution_status": exec_sim.status,
            "telemetry_changes": exec_sim.telemetry_changes,
        },
    )
    _audit(
        db,
        incident_id,
        "recovery_outcome_recorded",
        {"action_id": row.id, "outcome": exec_sim.status},
    )

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

    inv = db.get(InvestigationRow, row.investigation_id)
    incident_id = inv.incident_id if inv else "unknown"
    _audit(
        db,
        incident_id,
        "recovery_outcome_recorded",
        {"action_id": row.id, "outcome": outcome},
    )

    return _row_to_response(row)


def generate_postmortem(
    db: Session, investigation_id: str, custom_notes: str | None = None
) -> PostmortemDraft:
    """Generate and persist an automated postmortem for the given investigation."""
    inv = db.get(InvestigationRow, investigation_id)
    if inv is None:
        raise ValueError(f"Investigation '{investigation_id}' not found.")

    incident = db.get(IncidentRow, inv.incident_id)
    if incident is None:
        raise ValueError(f"Incident '{inv.incident_id}' not found.")

    # Find latest recovery action
    action_rows = (
        db.query(RecoveryActionRow)
        .filter(RecoveryActionRow.investigation_id == investigation_id)
        .order_by(RecoveryActionRow.created_at.desc())
        .all()
    )
    latest_action = action_rows[0] if action_rows else None

    # Gather audit events
    audit_rows = (
        db.query(AuditEntryRow)
        .filter(AuditEntryRow.incident_id == incident.id)
        .order_by(AuditEntryRow.created_at)
        .all()
    )
    audit_entries = [
        {"action": a.action, "actor": a.actor, "timestamp": a.created_at.isoformat()}
        for a in audit_rows
    ]

    action_dict = None
    if latest_action:
        action_dict = {
            "action": latest_action.action,
            "target": latest_action.target,
            "approval_status": latest_action.approval_status,
            "approved_by": latest_action.approved_by,
            "approved_at": latest_action.approved_at,
            "simulated_result": latest_action.simulated_result,
            "outcome": latest_action.outcome,
        }

    postmortem = generate_postmortem_draft(
        incident={
            "id": incident.id,
            "title": incident.title,
            "severity": incident.severity,
            "started_at": incident.started_at.isoformat() if incident.started_at else None,
            "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
            "recovered_at": incident.recovered_at.isoformat() if incident.recovered_at else None,
            "affected_services": incident.affected_services,
        },
        investigation={
            "id": inv.id,
            "evidence": inv.evidence,
            "hypotheses": inv.hypotheses,
            "challenge": inv.challenge,
        },
        recovery_action=action_dict,
        audit_entries=audit_entries,
        custom_notes=custom_notes,
    )

    inv.postmortem = postmortem.model_dump(mode="json")
    db.commit()
    db.refresh(inv)

    _audit(
        db,
        incident.id,
        "postmortem_generated",
        {"investigation_id": inv.id, "postmortem_title": postmortem.title},
    )

    return postmortem


def get_postmortem(db: Session, investigation_id: str) -> dict | None:
    inv = db.get(InvestigationRow, investigation_id)
    if inv is None:
        return None
    return inv.postmortem


def archive_incident_memory(
    db: Session, investigation_id: str
) -> IncidentMemoryResponse:
    """Archive a resolved incident and postmortem into historical memory."""
    inv = db.get(InvestigationRow, investigation_id)
    if inv is None:
        raise ValueError(f"Investigation '{investigation_id}' not found.")

    incident = db.get(IncidentRow, inv.incident_id)
    if incident is None:
        raise ValueError(f"Incident '{inv.incident_id}' not found.")

    # Get latest action
    action_rows = (
        db.query(RecoveryActionRow)
        .filter(RecoveryActionRow.investigation_id == investigation_id)
        .order_by(RecoveryActionRow.created_at.desc())
        .all()
    )
    latest_action = action_rows[0] if action_rows else None
    recovery_desc = latest_action.action if latest_action else "No recovery action"
    recovery_out = (
        (latest_action.outcome or latest_action.simulated_result or "completed")
        if latest_action else "completed"
    )

    # Ground-truth firewall (M2): ensure no hidden GT keys propagate into historical memory
    from app.ai.ground_truth import assert_no_ground_truth
    assert_no_ground_truth(inv.evidence or {})

    hypotheses = inv.hypotheses or []
    leading_hyp = hypotheses[0] if hypotheses else {}
    hyp_title = leading_hyp.get("title", "system-degradation").lower()

    # Deterministic fingerprint from visible services and symptoms
    services_str = " ".join(incident.affected_services)
    root_cause_cat = "system_regression"
    if "deployment" in hyp_title:
        root_cause_cat = "deployment_regression"
    elif "database" in hyp_title or "db" in hyp_title or "pool" in hyp_title:
        root_cause_cat = "database_exhaustion"
    elif "dependency" in hyp_title or "external" in hyp_title:
        root_cause_cat = "dependency_failure"
    elif "configuration" in hyp_title or "config" in hyp_title:
        root_cause_cat = "configuration_regression"

    fingerprint = f"{incident.scenario_id} {services_str} {root_cause_cat}"

    # Summaries of visible evidence
    evidence_summaries = []
    if inv.evidence:
        for ev in inv.evidence.get("evidence", [])[:5]:
            if isinstance(ev, dict) and ev.get("summary"):
                evidence_summaries.append(ev["summary"])

    create_payload = IncidentMemoryCreate(
        fingerprint=fingerprint,
        title=f"Resolved: {incident.title}",
        root_cause_category=root_cause_cat,
        evidence_summary=evidence_summaries,
        recovery_action=recovery_desc,
        recovery_outcome=recovery_out,
        scenario_id=incident.scenario_id,
        incident_id=incident.id,
    )

    mem = store_memory(db, create_payload)

    _audit(
        db,
        incident.id,
        "incident_memory_archived",
        {"memory_id": mem.id, "fingerprint": fingerprint},
    )

    return mem


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
# Legacy Deterministic simulation helper
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
