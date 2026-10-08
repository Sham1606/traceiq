"""Investigation service — orchestrates the deterministic evidence engine
and AI hypothesis generation.

AI calls use a stub that can be replaced with a real provider.
All LLM output is validated before persistence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.evidence import EvidenceEngine
from app.models.orm import AuditEntryRow, IncidentRow, InvestigationRow
from app.schemas.api import InvestigationResponse
from .hypotheses import generate_hypotheses


def _row_to_response(row: InvestigationRow) -> InvestigationResponse:
    return InvestigationResponse(
        id=row.id,
        incident_id=row.incident_id,
        status=row.status,
        evidence=row.evidence,
        hypotheses=row.hypotheses,
        challenge=row.challenge,
        postmortem=row.postmortem,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def start_investigation(db: Session, incident_id: str) -> InvestigationResponse | None:
    """Create and run a new investigation for the given incident.

    Returns None if the incident does not exist.
    Raises on evidence-engine or persistence failure (caller handles 500).
    """
    incident_row: IncidentRow | None = db.get(IncidentRow, incident_id)
    if incident_row is None:
        return None

    now = datetime.now(timezone.utc)
    inv = InvestigationRow(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        status="running",
        created_at=now,
        updated_at=now,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    _audit(db, incident_id, "investigation_started", {"investigation_id": inv.id})

    try:
        # --- Deterministic evidence engine ---
        engine = EvidenceEngine(settings.data_root)
        bundle = engine.investigate(incident_row.scenario_id)

        # Serialise evidence bundle (no ground truth is present)
        # mode='json' converts datetime → ISO string so json.dumps works
        evidence_dict = bundle.model_dump(mode="json")

        # --- AI hypothesis generation with deterministic fallback ---
        import app.ai.config as ai_config
        import app.ai.graph as ai_graph
        import app.ai.providers as ai_providers
        import app.ai.state as ai_state

        if ai_config.ai_settings.enabled:
            try:
                ai_provider = ai_providers.get_ai_provider(ai_config.ai_settings)

                # Query historical memory using observable fingerprint
                historical_matches: list[dict] = []
                try:
                    from app.ai.historical import build_fingerprint_from_evidence
                    from app.services.investigation.memory import search_memory

                    inc_context = {
                        "id": incident_row.id,
                        "severity": incident_row.severity,
                        "affected_services": incident_row.affected_services,
                    }
                    fingerprint = build_fingerprint_from_evidence(evidence_dict, inc_context)
                    mem_response = search_memory(db, fingerprint, limit=3)
                    if mem_response and mem_response.matches:
                        historical_matches = [
                            m.model_dump(mode="json") for m in mem_response.matches
                        ]
                except Exception:
                    historical_matches = []

                state = ai_state.create_initial_state(
                    incident_row,
                    bundle,
                    provider=ai_provider.provider_name,
                    model=ai_provider.model_name,
                    historical_context=historical_matches,
                )
                final_state = ai_graph.run_investigation_graph(state, provider=ai_provider)
                if final_state.get("plan"):
                    evidence_dict["plan"] = final_state["plan"]
                if final_state.get("findings"):
                    evidence_dict["investigator_findings"] = final_state["findings"]
                if final_state.get("correlations"):
                    evidence_dict["correlations"] = final_state["correlations"]
                if final_state.get("challenge"):
                    inv.challenge = final_state["challenge"]

                if final_state.get("hypotheses"):
                    inv.hypotheses = final_state["hypotheses"]
                    _audit(
                        db,
                        incident_id,
                        "ai_investigation_completed",
                        {
                            "provider": ai_provider.provider_name,
                            "model": ai_provider.model_name,
                            "finding_count": len(final_state.get("findings", [])),
                        },
                    )
                else:
                    hypotheses = generate_hypotheses(bundle)
                    inv.hypotheses = [h.model_dump() for h in hypotheses]
            except Exception as ai_exc:  # noqa: BLE001
                _audit(db, incident_id, "ai_investigation_fallback", {"error": str(ai_exc)})
                hypotheses = generate_hypotheses(bundle)
                inv.hypotheses = [h.model_dump() for h in hypotheses]
        else:
            hypotheses = generate_hypotheses(bundle)
            inv.hypotheses = [h.model_dump() for h in hypotheses]

        inv.evidence = evidence_dict
        inv.status = "complete"

    except Exception as exc:  # noqa: BLE001
        inv.status = "failed"
        inv.evidence = None
        inv.hypotheses = None
        inv.challenge = None
        _audit(db, incident_id, "investigation_failed", {"error": str(exc)})
    finally:
        inv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(inv)

    if inv.status == "complete":
        _audit(db, incident_id, "investigation_complete", {"investigation_id": inv.id})

    return _row_to_response(inv)


def get_investigation(db: Session, investigation_id: str) -> InvestigationResponse | None:
    row = db.get(InvestigationRow, investigation_id)
    if row is None:
        return None
    return _row_to_response(row)


def list_investigations(db: Session, incident_id: str) -> list[InvestigationResponse]:
    rows = (
        db.query(InvestigationRow)
        .filter(InvestigationRow.incident_id == incident_id)
        .order_by(InvestigationRow.created_at.desc())
        .all()
    )
    return [_row_to_response(r) for r in rows]


def _audit(db: Session, incident_id: str, action: str, detail: dict) -> None:
    entry = AuditEntryRow(
        incident_id=incident_id,
        action=action,
        actor="system",
        created_at=datetime.now(timezone.utc),
    )
    entry.detail = detail
    db.add(entry)
    db.commit()
