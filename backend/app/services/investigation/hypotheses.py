"""Deterministic hypothesis generator.

This is the AI-stub layer for Phase 3. It produces structured, validated
Hypothesis objects from the evidence bundle without calling any LLM.

The interface is designed so a real LLM provider can be plugged in later:
- The function signature stays the same.
- The caller validates the returned list[HypothesisSchema].
- Malformed output → reject/retry/fallback (currently no retry needed).

Ground truth is NEVER passed into this function.
"""
from __future__ import annotations

from app.evidence.models import EvidenceBundle, MetricFinding
from .schemas import HypothesisSchema, EvidenceStrengthLabel


def _pick_strength(anomalous_count: int, contradiction_count: int) -> EvidenceStrengthLabel:
    if anomalous_count == 0:
        return "inconclusive"
    if contradiction_count >= anomalous_count:
        return "weakly_supported"
    if anomalous_count >= 3:
        return "strongly_supported"
    if anomalous_count >= 2:
        return "supported"
    return "weakly_supported"


def _metric_anomalies(bundle: EvidenceBundle) -> list[MetricFinding]:
    return [f for f in bundle.metric_findings if f.anomaly]


def _build_hypotheses(bundle: EvidenceBundle) -> list[HypothesisSchema]:
    hypotheses: list[HypothesisSchema] = []
    anomalies = _metric_anomalies(bundle)

    # Group anomalies by service
    by_service: dict[str, list[MetricFinding]] = {}
    for a in anomalies:
        by_service.setdefault(a.service, []).append(a)

    ev_ids = [ev["id"] for ev in bundle.evidence]
    supporting_ids = [ev["id"] for ev in bundle.evidence if ev.get("strength") in {"strongly_supported", "supported"}]
    contradicting_ids = [ev["id"] for ev in bundle.evidence if ev.get("contradicts")]

    timeline_events = bundle.timeline_findings
    has_deployment = any(t.event_type == "deployment" for t in timeline_events)
    has_config = any(t.event_type == "configuration" for t in timeline_events)
    has_dependency = any(t.event_type == "dependency" for t in timeline_events)

    h_index = 1

    # Hypothesis: deployment regression
    if has_deployment and anomalies:
        h = HypothesisSchema(
            id=f"hyp-{h_index:02d}",
            title="Application regression introduced by a recent deployment",
            explanation=(
                f"A deployment event precedes the incident window. "
                f"{len(anomalies)} metric anomalies and "
                f"{len(bundle.log_findings)} log patterns were observed. "
                "The deployment may have introduced a regression."
            ),
            evidence_ids=ev_ids[:10],
            supporting_evidence_ids=supporting_ids[:5],
            contradicting_evidence_ids=contradicting_ids[:3],
            strength=_pick_strength(len(anomalies), len(contradicting_ids)),
        )
        hypotheses.append(h)
        h_index += 1

    # Hypothesis: database degradation
    db_services = [s for s in by_service if "db" in s or "database" in s or "postgres" in s]
    if db_services:
        db_anomalies = sum(len(by_service[s]) for s in db_services)
        h = HypothesisSchema(
            id=f"hyp-{h_index:02d}",
            title="Database performance degradation",
            explanation=(
                f"Services {', '.join(db_services)} show {db_anomalies} metric anomalies. "
                "Query latency or connection utilization may have degraded."
            ),
            evidence_ids=[ev["id"] for ev in bundle.evidence if any(s in ev.get("source_id", "") for s in db_services)][:10],
            supporting_evidence_ids=supporting_ids[:5],
            contradicting_evidence_ids=[],
            strength=_pick_strength(db_anomalies, 0),
        )
        hypotheses.append(h)
        h_index += 1

    # Hypothesis: external dependency failure
    if has_dependency:
        dep_findings = [t for t in timeline_events if t.event_type == "dependency"]
        h = HypothesisSchema(
            id=f"hyp-{h_index:02d}",
            title="External dependency degradation or failure",
            explanation=(
                f"{len(dep_findings)} dependency degradation events observed during the incident window. "
                "An external service may be unavailable or slow."
            ),
            evidence_ids=ev_ids[:10],
            supporting_evidence_ids=supporting_ids[:5],
            contradicting_evidence_ids=contradicting_ids[:3],
            strength=_pick_strength(len(dep_findings), len(contradicting_ids)),
        )
        hypotheses.append(h)
        h_index += 1

    # Hypothesis: configuration regression
    if has_config:
        h = HypothesisSchema(
            id=f"hyp-{h_index:02d}",
            title="Configuration change caused a regression",
            explanation=(
                "A configuration change was applied during or before the incident window. "
                "Misconfigured parameters may have caused service degradation."
            ),
            evidence_ids=ev_ids[:8],
            supporting_evidence_ids=supporting_ids[:4],
            contradicting_evidence_ids=contradicting_ids[:2],
            strength=_pick_strength(len(anomalies), len(contradicting_ids)),
        )
        hypotheses.append(h)
        h_index += 1

    # Fallback: always return at least one hypothesis
    if not hypotheses:
        hypotheses.append(
            HypothesisSchema(
                id="hyp-01",
                title="Undetermined root cause",
                explanation="Insufficient evidence to form a specific hypothesis. Continue investigation.",
                evidence_ids=ev_ids[:5],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                strength="inconclusive",
            )
        )

    return hypotheses


def generate_hypotheses(bundle: EvidenceBundle) -> list[HypothesisSchema]:
    """Entry point. Returns validated hypotheses; never exposes ground truth."""
    try:
        result = _build_hypotheses(bundle)
        # Validate — would reject malformed LLM output here
        for h in result:
            assert h.id and h.title and h.strength
        return result
    except Exception:  # noqa: BLE001
        return [
            HypothesisSchema(
                id="hyp-fallback",
                title="Hypothesis generation failed — evidence inconclusive",
                explanation="The hypothesis generator encountered an error. Falling back to inconclusive.",
                evidence_ids=[],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                strength="inconclusive",
            )
        ]
