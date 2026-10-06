"""Investigation API router (B003)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import InvestigationResponse
from app.services.investigation import start_investigation, get_investigation, list_investigations

router = APIRouter(tags=["investigations"])


@router.post("/incidents/{incident_id}/investigations", response_model=InvestigationResponse, status_code=201)
def start(incident_id: str, db: Session = Depends(get_db)):
    result = start_investigation(db, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.get("/incidents/{incident_id}/investigations", response_model=list[InvestigationResponse])
def list_for_incident(incident_id: str, db: Session = Depends(get_db)):
    return list_investigations(db, incident_id)


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
def get_one(investigation_id: str, db: Session = Depends(get_db)):
    result = get_investigation(db, investigation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return result
