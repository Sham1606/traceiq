"""Historical incident memory service (B004).

Deterministic fingerprint-based similarity retrieval.
Historical matches are supporting evidence only — never automatic truth.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.orm import IncidentMemoryRow
from app.schemas.api import (
    IncidentMemoryCreate,
    IncidentMemoryResponse,
    MemoryMatch,
    MemorySearchResponse,
)


def _row_to_response(row: IncidentMemoryRow) -> IncidentMemoryResponse:
    return IncidentMemoryResponse(
        id=row.id,
        fingerprint=row.fingerprint,
        title=row.title,
        root_cause_category=row.root_cause_category,
        evidence_summary=row.evidence_summary,
        recovery_action=row.recovery_action,
        recovery_outcome=row.recovery_outcome,
        scenario_id=row.scenario_id,
        incident_id=row.incident_id,
        created_at=row.created_at,
    )


def store_memory(db: Session, payload: IncidentMemoryCreate) -> IncidentMemoryResponse:
    row = IncidentMemoryRow(
        id=str(uuid.uuid4()),
        fingerprint=payload.fingerprint,
        title=payload.title,
        root_cause_category=payload.root_cause_category,
        recovery_action=payload.recovery_action,
        recovery_outcome=payload.recovery_outcome,
        scenario_id=payload.scenario_id,
        incident_id=payload.incident_id,
        created_at=datetime.now(timezone.utc),
    )
    row.evidence_summary = payload.evidence_summary
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


def search_memory(db: Session, fingerprint: str, limit: int = 5) -> MemorySearchResponse:
    """Return incidents whose fingerprint shares tokens with the query.

    Uses token overlap — no vectors needed for MVP.
    Historical matches are labelled as supporting evidence with match notes.
    """
    query_tokens = set(_tokenize(fingerprint))
    all_rows = db.query(IncidentMemoryRow).all()

    matches: list[tuple[int, list[str], IncidentMemoryRow]] = []
    for row in all_rows:
        row_tokens = set(_tokenize(row.fingerprint))
        shared = list(query_tokens & row_tokens)
        if shared:
            matches.append((len(shared), shared, row))

    matches.sort(key=lambda x: -x[0])
    top = matches[:limit]

    match_items = [
        MemoryMatch(
            memory=_row_to_response(row),
            shared_fingerprint_tokens=shared,
            match_note=(
                f"Historical incident shares {len(shared)} fingerprint token(s). "
                "Treat as supporting context only; validate against current evidence."
            ),
        )
        for _, shared, row in top
    ]

    return MemorySearchResponse(
        query_fingerprint=fingerprint,
        matches=match_items,
    )


def get_memory(db: Session, memory_id: str) -> IncidentMemoryResponse | None:
    row = db.get(IncidentMemoryRow, memory_id)
    if row is None:
        return None
    return _row_to_response(row)


def _tokenize(fingerprint: str) -> list[str]:
    """Split fingerprint into lowercase tokens on non-alphanumeric separators."""
    import re
    return [t for t in re.split(r"[^a-z0-9]+", fingerprint.lower()) if t]
