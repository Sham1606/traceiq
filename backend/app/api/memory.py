"""Historical memory API router (B004)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.api import IncidentMemoryCreate, IncidentMemoryResponse, MemorySearchResponse
from app.services.investigation.memory import store_memory, search_memory, get_memory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=IncidentMemoryResponse, status_code=201)
def store(payload: IncidentMemoryCreate, db: Session = Depends(get_db)):
    return store_memory(db, payload)


@router.get("/search", response_model=MemorySearchResponse)
def search(
    fingerprint: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return search_memory(db, fingerprint, limit=limit)


@router.get("/{memory_id}", response_model=IncidentMemoryResponse)
def get_one(memory_id: str, db: Session = Depends(get_db)):
    result = get_memory(db, memory_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return result
