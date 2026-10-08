"""Incident CRUD service — no business logic beyond persistence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.orm import IncidentRow
from app.schemas.api import IncidentCreate, IncidentResponse, LiveIncidentCreate


def _row_to_response(row: IncidentRow) -> IncidentResponse:
    return IncidentResponse(
        id=row.id,
        scenario_id=row.scenario_id,
        title=row.title,
        status=row.status,
        severity=row.severity,
        started_at=row.started_at,
        detected_at=row.detected_at,
        recovered_at=row.recovered_at,
        affected_services=row.affected_services,
        description=row.description,
        created_at=row.created_at,
        custom_evidence=row.custom_evidence,
    )


def create_incident(db: Session, payload: IncidentCreate) -> IncidentResponse:
    if payload.detected_at < payload.started_at:
        raise ValueError("detected_at must be >= started_at")
    row = IncidentRow(
        id=str(uuid.uuid4()),
        scenario_id=payload.scenario_id,
        title=payload.title,
        status="open",
        severity=payload.severity,
        started_at=payload.started_at,
        detected_at=payload.detected_at,
        recovered_at=payload.recovered_at,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
    )
    row.affected_services = payload.affected_services
    if payload.custom_evidence:
        row.custom_evidence = payload.custom_evidence
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def create_live_incident(db: Session, payload: LiveIncidentCreate) -> IncidentResponse:
    """Create a new custom incident from Live Incident Lab with supplied evidence."""
    now = datetime.now(timezone.utc)
    started = payload.started_at or now
    detected = payload.detected_at or now
    recovered = payload.recovered_at or now

    row = IncidentRow(
        id=str(uuid.uuid4()),
        scenario_id="LIVE_CUSTOM",
        title=payload.title,
        status="open",
        severity=payload.severity,
        started_at=started,
        detected_at=detected,
        recovered_at=recovered,
        description=payload.description,
        created_at=now,
    )
    row.affected_services = payload.affected_services
    row.custom_evidence = payload.evidence_items
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def list_incidents(db: Session, skip: int = 0, limit: int = 50) -> tuple[int, list[IncidentResponse]]:
    total = db.query(IncidentRow).count()
    rows = db.query(IncidentRow).order_by(IncidentRow.created_at.desc()).offset(skip).limit(limit).all()
    return total, [_row_to_response(r) for r in rows]


def get_incident(db: Session, incident_id: str) -> IncidentResponse | None:
    row = db.get(IncidentRow, incident_id)
    if row is None:
        return None
    return _row_to_response(row)


def update_incident_status(db: Session, incident_id: str, status: str) -> IncidentResponse | None:
    row = db.get(IncidentRow, incident_id)
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return _row_to_response(row)
