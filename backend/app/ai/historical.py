"""Historical incident reasoning for TRACEIQ Phase 5.3.

Provides a database-free (graph-safe) version of historical reasoning that
uses pre-loaded historical context rather than live DB queries.

Architecture rules:
- Historical incidents are SUPPORTING CONTEXT ONLY — never automatic truth.
- A historical match does NOT override current evidence.
- The match score is based only on observable telemetry similarity
  (fingerprint token overlap), never on ground truth fields.
- Hypotheses may be *annotated* with historical context but cannot be
  CONFIRMED by historical context alone.
- If historical context is empty or unavailable, reasoning proceeds without it.
- No database session is used here; the DB lookup happens in the graph node
  which passes pre-fetched matches into this module.
"""
from __future__ import annotations

from typing import Any


def build_historical_context_note(
    historical_matches: list[dict[str, Any]],
) -> str:
    """Build a textual historical context note for hypothesis annotation.

    This note is purely informational and is attached to the hypothesis
    metadata — it does not change the hypothesis strength or evidence IDs.

    Parameters
    ----------
    historical_matches:
        List of serialised MemoryMatch dicts (from MemorySearchResponse.matches).
        Each item may contain 'memory' (IncidentMemoryResponse) and
        'shared_fingerprint_tokens' and 'match_note'.

    Returns
    -------
    A human-readable context string, or empty string if no matches.
    """
    if not historical_matches:
        return ""

    lines: list[str] = [
        f"Historical context: {len(historical_matches)} similar past incident(s) found."
    ]
    for i, match in enumerate(historical_matches[:3], start=1):
        memory = match.get("memory") or match
        title = memory.get("title") or "Untitled incident"
        category = memory.get("root_cause_category") or "unknown"
        shared = match.get("shared_fingerprint_tokens") or []
        note = match.get("match_note") or ""
        lines.append(
            f"  [{i}] '{title}' (category: {category}). "
            f"Shared signals: {shared[:5]}. {note}"
        )

    lines.append(
        "NOTE: Historical matches are supporting context only. "
        "They do not confirm the current hypothesis. "
        "Validate all conclusions against current evidence."
    )
    return "\n".join(lines)


def enrich_hypotheses_with_historical_context(
    hypotheses: list[dict[str, Any]],
    historical_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate hypotheses with historical context without altering their strength or evidence IDs.

    The historical context is stored in the hypothesis's metadata field only.
    No evidence_ids or supporting_evidence_ids are added from history because
    historical incident IDs are NOT present in the current evidence bundle.

    Parameters
    ----------
    hypotheses:
        List of serialised AIHypothesis dicts.
    historical_matches:
        List of serialised MemoryMatch dicts.

    Returns
    -------
    Annotated list of hypothesis dicts (metadata enriched, structure unchanged).
    """
    if not historical_matches or not hypotheses:
        return hypotheses

    note = build_historical_context_note(historical_matches)
    if not note:
        return hypotheses

    # Extract category patterns from historical matches for weak annotation
    historical_categories: list[str] = []
    for match in historical_matches:
        memory = match.get("memory") or match
        cat = memory.get("root_cause_category") or ""
        if cat and cat not in historical_categories:
            historical_categories.append(cat)

    enriched: list[dict[str, Any]] = []
    for hyp in hypotheses:
        h = dict(hyp)
        # Preserve all existing metadata; add historical context
        metadata = dict(h.get("metadata") or {}) if isinstance(h.get("metadata"), dict) else {}
        metadata["historical_context_note"] = note
        metadata["historical_categories_observed"] = historical_categories[:5]
        metadata["historical_match_count"] = len(historical_matches)
        metadata["historical_override"] = False  # explicitly mark as non-overriding
        h["metadata"] = metadata
        enriched.append(h)

    return enriched


def build_fingerprint_from_evidence(evidence: dict[str, Any], incident: dict[str, Any]) -> str:
    """Build a similarity fingerprint from observable evidence signals.

    Used to search historical memory for similar past incidents.
    The fingerprint is built from observable telemetry — never from ground truth.

    Parameters
    ----------
    evidence:
        Sanitised evidence bundle.
    incident:
        Incident context dict.

    Returns
    -------
    A space-separated fingerprint string for token-based similarity matching.
    """
    tokens: list[str] = []

    # Incident context (observable metadata)
    severity = str(incident.get("severity") or "")
    if severity:
        tokens.append(severity)

    for svc in (incident.get("affected_services") or [])[:3]:
        tokens.append(str(svc).lower().replace("-", "_"))

    # Timeline event types
    for t in (evidence.get("timeline_findings") or [])[:5]:
        ev_type = str(t.get("event_type") or "")
        if ev_type:
            tokens.append(ev_type)

    # Metric anomaly types
    for m in (evidence.get("metric_findings") or [])[:5]:
        if m.get("anomaly"):
            metric = str(m.get("metric") or "")
            if metric:
                tokens.append(metric)

    # Log error patterns (high-level summary keywords only)
    for log in (evidence.get("log_findings") or [])[:3]:
        if log.get("error_or_warn_count", 0) > 0:
            svc = str(log.get("service") or "")
            if svc:
                tokens.append(svc.lower().replace("-", "_"))

    return " ".join(tokens) if tokens else "unknown"
