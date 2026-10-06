"""Incident API router (B002)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import IncidentCreate, IncidentList, IncidentResponse
from app.services.incident import create_incident, get_incident, list_incidents

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
def create(payload: IncidentCreate, db: Session = Depends(get_db)):
    try:
        return create_incident(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=IncidentList)
def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total, items = list_incidents(db, skip=skip, limit=limit)
    return IncidentList(total=total, items=items)


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_one(incident_id: str, db: Session = Depends(get_db)):
    result = get_incident(db, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result
