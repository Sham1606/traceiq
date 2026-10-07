"""Deterministic cross-investigator correlation engine for TRACEIQ Phase 5.3.

Correlates findings from multiple domain investigators to identify:
1. Shared evidence IDs that appear in more than one domain finding.
2. Temporal causal sequence derived from timeline events.
3. False-lead domains whose evidence does NOT align with the primary signal.
4. Contradicting evidence that should weaken the leading hypothesis.

Architecture rules enforced here:
- No ground truth is received, stored, or referenced.
- All evidence IDs are validated against the evidence bundle BEFORE being
  written into the CorrelationFinding.
- Deterministic output: identical inputs produce identical outputs.
- AI provider is OPTIONAL; if provided and non-mock it may annotate the
  correlation summary, but the structural content is always deterministic.
"""
from __future__ import annotations

import uuid
from typing import Any

from .schemas import CorrelationFinding, EvidenceStrengthLabel
from .validation import extract_valid_evidence_ids, validate_evidence_ids


def correlate_findings(
    findings: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> CorrelationFinding:
    """Produce a deterministic cross-investigator correlation finding.

    Parameters
    ----------
    findings:
        List of serialised InvestigatorFinding dicts from domain investigators.
    evidence:
        The sanitised evidence bundle dict (ground truth already stripped).

    Returns
    -------
    CorrelationFinding with validated evidence IDs.
    """
    valid_ids = extract_valid_evidence_ids(evidence)

    # ------------------------------------------------------------------ #
    # 1. Collect all evidence IDs cited by each domain investigator.       #
    # ------------------------------------------------------------------ #
    domain_to_ids: dict[str, set[str]] = {}
    for f in findings:
        domain = f.get("investigator_type") or f.get("domain") or "unknown"
        ids: set[str] = set()
        for field in ("evidence_ids", "supporting_evidence_ids"):
            for eid in f.get(field, []):
                if str(eid) in valid_ids:
                    ids.add(str(eid))
        domain_to_ids[domain] = ids

    # ------------------------------------------------------------------ #
    # 2. Shared evidence: IDs cited by ≥2 domain investigators.           #
    # ------------------------------------------------------------------ #
    all_id_counts: dict[str, int] = {}
    for ids in domain_to_ids.values():
        for eid in ids:
            all_id_counts[eid] = all_id_counts.get(eid, 0) + 1

    shared_ids = sorted(eid for eid, cnt in all_id_counts.items() if cnt >= 2)

    # ------------------------------------------------------------------ #
    # 3. Domains with at least one supporting evidence ID = correlated.   #
    #    Domains with zero valid evidence IDs = potential false leads.     #
    # ------------------------------------------------------------------ #
    correlated_domains: list[str] = []
    false_lead_domains: list[str] = []
    for domain, ids in domain_to_ids.items():
        if ids:
            correlated_domains.append(domain)
        else:
            false_lead_domains.append(domain)

    # ------------------------------------------------------------------ #
    # 4. Contradicting evidence from findings.                            #
    # ------------------------------------------------------------------ #
    contradicting_ids: list[str] = []
    for f in findings:
        for eid in f.get("contradicting_evidence_ids", []):
            if str(eid) in valid_ids and str(eid) not in contradicting_ids:
                contradicting_ids.append(str(eid))

    # ------------------------------------------------------------------ #
    # 5. Causal sequence from timeline events (deterministic ordering).   #
    # ------------------------------------------------------------------ #
    timeline = evidence.get("timeline_findings", [])
    # Sort by timestamp if available; otherwise use order as-is
    def _ts_key(t: dict[str, Any]) -> str:
        return str(t.get("timestamp") or t.get("event_time") or "")

    sorted_timeline = sorted(timeline, key=_ts_key)
    causal_sequence: list[str] = []
    for t in sorted_timeline[:8]:  # cap at 8 events
        ev_type = t.get("event_type", "event")
        summary = t.get("summary", "")
        if summary:
            causal_sequence.append(f"[{ev_type.upper()}] {summary}")

    # ------------------------------------------------------------------ #
    # 6. Strength: based on shared signal density and false leads.        #
    # ------------------------------------------------------------------ #
    n_correlated = len(correlated_domains)
    n_shared = len(shared_ids)
    n_contradicting = len(contradicting_ids)

    strength: EvidenceStrengthLabel
    if n_correlated == 0:
        strength = "inconclusive"
    elif n_shared >= 3 and n_contradicting == 0:
        strength = "strongly_supported"
    elif n_shared >= 1 and n_contradicting <= n_shared:
        strength = "supported"
    elif n_contradicting > n_shared:
        strength = "weakly_supported"
    else:
        strength = "inconclusive"

    # ------------------------------------------------------------------ #
    # 7. Narrative summary.                                               #
    # ------------------------------------------------------------------ #
    if correlated_domains:
        domain_list = ", ".join(sorted(correlated_domains))
        summary = (
            f"Cross-investigator correlation found {n_shared} shared evidence signal(s) "
            f"across domains: {domain_list}. "
        )
        if false_lead_domains:
            summary += (
                f"Domain(s) {', '.join(sorted(false_lead_domains))} produced no "
                "validated evidence and are marked as potential false leads. "
            )
        if causal_sequence:
            summary += f"Causal sequence of {len(causal_sequence)} events established from timeline."
    else:
        summary = (
            "No shared evidence signals found across domain investigators. "
            "Each domain produced isolated or empty findings. Correlation inconclusive."
        )

    # ------------------------------------------------------------------ #
    # 8. Final validation of all IDs before writing.                      #
    # ------------------------------------------------------------------ #
    validate_evidence_ids(shared_ids, valid_ids, field_name="correlation.shared_evidence_ids")
    validate_evidence_ids(contradicting_ids, valid_ids, field_name="correlation.contradicting_evidence_ids")

    return CorrelationFinding(
        correlation_id=f"corr-{uuid.uuid4().hex[:8]}",
        correlated_domains=sorted(correlated_domains),
        shared_evidence_ids=shared_ids[:10],
        causal_sequence=causal_sequence,
        false_lead_domains=sorted(false_lead_domains),
        contradicting_evidence_ids=contradicting_ids[:5],
        summary=summary,
        strength=strength,
    )
