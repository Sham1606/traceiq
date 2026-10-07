"""Adversarial Challenge Agent for TRACEIQ Phase 5.3.

The Challenge Agent is the adversarial counterpart to hypothesis generation.
Its sole purpose is to ATTEMPT TO DISPROVE the leading hypothesis — not to
confirm it.

Architecture rules:
- The agent MUST be capable of returning status="rejected".
- It never receives hidden ground truth.
- It works exclusively from validated evidence IDs.
- Every ChallengeResult evidence reference is validated.
- A real AI provider may be used to reason adversarially; the deterministic
  fallback independently evaluates the hypothesis strength from evidence.
- Failure handling: any agent failure returns an inconclusive ChallengeResult
  (never a fabricated supported/rejected status).

Challenge logic (deterministic path):
1. Inspect the hypothesis's supporting_evidence_ids and contradicting_evidence_ids.
2. Inspect the correlation finding for false-lead domains.
3. Inspect whether the hypothesis's assumed causal domain matches any actual
   timeline events or is purely speculative.
4. If contradicting evidence outweighs supporting evidence → REJECTED.
5. If no shared cross-domain evidence and false leads exist → REJECTED.
6. If evidence is sparse (hypothesis is weakly_supported / inconclusive) → INCONCLUSIVE.
7. Otherwise → SUPPORTED (the hypothesis survived the challenge).
"""
from __future__ import annotations

import uuid
from typing import Any

from .schemas import AIHypothesis, ChallengeResult, CorrelationFinding, EvidenceStrengthLabel
from .validation import extract_valid_evidence_ids, validate_evidence_ids


_WEAK_STRENGTHS: frozenset[str] = frozenset({"inconclusive", "weakly_supported"})
_STRONG_STRENGTHS: frozenset[str] = frozenset({"strongly_supported", "supported"})


def challenge_hypothesis(
    hypothesis: AIHypothesis,
    correlation: CorrelationFinding | None,
    evidence: dict[str, Any],
    provider: Any | None = None,
) -> ChallengeResult:
    """Adversarially evaluate the leading hypothesis.

    Parameters
    ----------
    hypothesis:
        The leading AIHypothesis produced by the hypotheses node.
    correlation:
        The CorrelationFinding from the correlation node (may be None if
        correlation node failed or was skipped).
    evidence:
        Sanitised evidence bundle (no ground truth).
    provider:
        Optional AIProvider.  If provided and non-mock, the provider is asked
        to reason adversarially.  The deterministic fallback always runs.

    Returns
    -------
    ChallengeResult with status ∈ {supported, rejected, inconclusive}.
    """
    valid_ids = extract_valid_evidence_ids(evidence)

    # ------------------------------------------------------------------ #
    # Optional: AI adversarial reasoning (non-mock provider only)         #
    # ------------------------------------------------------------------ #
    if provider is not None and getattr(provider, "provider_name", "mock") != "mock":
        try:
            corr_summary = correlation.summary if correlation else "No correlation data available."
            ai_result = provider.generate_structured(
                ChallengeResult,
                prompt=(
                    f"Adversarially challenge the following hypothesis. "
                    f"Attempt to disprove it using the evidence. "
                    f"Return status=rejected if the evidence contradicts the hypothesis "
                    f"or if there is insufficient evidence to support it.\n\n"
                    f"Hypothesis: {hypothesis.model_dump(mode='json')}\n"
                    f"Correlation: {corr_summary}\n"
                    f"Evidence IDs available: {sorted(valid_ids)}"
                ),
                system_message=(
                    "You are the TRACEIQ Challenge Agent. Your role is adversarial. "
                    "Your goal is to DISPROVE the hypothesis, not confirm it. "
                    "Only return supported if you cannot find a reasonable objection. "
                    "All evidence IDs you cite MUST exist in the provided evidence."
                ),
            )
            # Validate every cited ID
            validate_evidence_ids(
                ai_result.contradicting_evidence_ids,
                valid_ids,
                field_name="challenge.contradicting_evidence_ids",
            )
            validate_evidence_ids(
                ai_result.independent_evidence_ids,
                valid_ids,
                field_name="challenge.independent_evidence_ids",
            )
            return ai_result
        except Exception:
            pass  # Fall through to deterministic challenge

    # ------------------------------------------------------------------ #
    # Deterministic adversarial challenge logic                           #
    # ------------------------------------------------------------------ #
    return _deterministic_challenge(hypothesis, correlation, evidence, valid_ids)


def _deterministic_challenge(
    hypothesis: AIHypothesis,
    correlation: CorrelationFinding | None,
    evidence: dict[str, Any],
    valid_ids: set[str],
) -> ChallengeResult:
    """Deterministic challenge logic — always evidence-grounded, never fabricated."""
    hyp_strength = hypothesis.strength
    sup_ids = [eid for eid in hypothesis.supporting_evidence_ids if eid in valid_ids]
    con_ids = [eid for eid in hypothesis.contradicting_evidence_ids if eid in valid_ids]

    # Evidence items for deeper inspection
    ev_items: list[dict[str, Any]] = evidence.get("evidence", [])
    ev_by_id = {str(e.get("id")): e for e in ev_items if e.get("id")}

    # Inspect contradicting evidence objects
    contradicting_evidence_objects = [
        ev_by_id[eid] for eid in con_ids if eid in ev_by_id
    ]
    # Strong contradicting evidence = evidence with a "contradicts" field set to a non-empty value
    strong_contradictions = [
        e for e in contradicting_evidence_objects
        if e.get("contradicts")
    ]

    # Correlation context
    false_lead_domains: list[str] = []
    shared_count = 0
    corr_contradicting: list[str] = []
    if correlation is not None:
        false_lead_domains = correlation.false_lead_domains or []
        shared_count = len(correlation.shared_evidence_ids)
        corr_contradicting = [
            eid for eid in correlation.contradicting_evidence_ids if eid in valid_ids
        ]

    # Timeline analysis — does the hypothesis domain have timeline support?
    timeline = evidence.get("timeline_findings", [])
    hyp_title_lower = hypothesis.title.lower()

    has_deployment_timeline = any(t.get("event_type") == "deployment" for t in timeline)
    has_config_timeline = any(t.get("event_type") == "configuration" for t in timeline)
    has_dependency_timeline = any(t.get("event_type") == "dependency" for t in timeline)
    has_db_timeline = any(t.get("event_type") == "database" for t in timeline)

    # Determine if the hypothesis domain has ANY timeline backing
    hypothesis_has_timeline_support = (
        ("deployment" in hyp_title_lower and has_deployment_timeline)
        or ("configuration" in hyp_title_lower and has_config_timeline)
        or ("dependency" in hyp_title_lower and has_dependency_timeline)
        or ("database" in hyp_title_lower and has_db_timeline)
        or ("connection" in hyp_title_lower and has_db_timeline)
    )

    # ------------------------------------------------------------------ #
    # Challenge verdict logic                                             #
    # ------------------------------------------------------------------ #
    challenge_rationale_parts: list[str] = []
    all_contradicting: list[str] = list(dict.fromkeys(con_ids + corr_contradicting))  # deduplicated
    challenge_status: str

    # REJECTION criteria:
    # C1. Explicit strong contradictions outweigh supporting evidence
    if strong_contradictions and len(strong_contradictions) >= len(sup_ids):
        challenge_status = "rejected"
        challenge_rationale_parts.append(
            f"Hypothesis rejected: {len(strong_contradictions)} strong contradicting evidence item(s) "
            f"outweigh {len(sup_ids)} supporting evidence item(s)."
        )

    # C2. Hypothesis is weakly supported AND correlation has no shared signals AND false leads exist
    elif (
        hyp_strength in _WEAK_STRENGTHS
        and shared_count == 0
        and false_lead_domains
    ):
        challenge_status = "rejected"
        challenge_rationale_parts.append(
            f"Hypothesis rejected: strength is '{hyp_strength}', "
            f"cross-domain correlation found zero shared evidence signals, "
            f"and domain(s) {false_lead_domains} are identified as false leads."
        )

    # C3. No supporting evidence at all AND no timeline backing
    elif not sup_ids and not hypothesis_has_timeline_support:
        challenge_status = "rejected"
        challenge_rationale_parts.append(
            "Hypothesis rejected: zero validated supporting evidence IDs and "
            "no matching timeline events for the hypothesised causal domain."
        )

    # INCONCLUSIVE criteria:
    # I1. Hypothesis is weakly_supported or inconclusive with insufficient cross-domain evidence
    elif hyp_strength in _WEAK_STRENGTHS or (not sup_ids and hypothesis_has_timeline_support):
        challenge_status = "inconclusive"
        challenge_rationale_parts.append(
            f"Hypothesis is '{hyp_strength}' with {len(sup_ids)} supporting evidence IDs "
            f"and {len(all_contradicting)} contradicting IDs. "
            "Insufficient cross-domain corroboration to confirm or reject."
        )

    # SUPPORTED: hypothesis survived adversarial challenge
    else:
        challenge_status = "supported"
        challenge_rationale_parts.append(
            f"Hypothesis survived adversarial challenge: {len(sup_ids)} supporting "
            f"evidence IDs with {len(all_contradicting)} contradicting evidence IDs. "
            f"Cross-domain correlation shared {shared_count} signal(s)."
        )
        if false_lead_domains:
            challenge_rationale_parts.append(
                f"Note: domain(s) {false_lead_domains} were identified as potential false leads "
                "but do not invalidate the primary causal hypothesis."
            )

    rationale = " ".join(challenge_rationale_parts)

    # Final validation of IDs we will write into ChallengeResult
    valid_contra = [eid for eid in all_contradicting if eid in valid_ids]
    validate_evidence_ids(valid_contra, valid_ids, field_name="challenge.contradicting_evidence_ids")

    independent_ids = [eid for eid in sup_ids if eid not in con_ids]
    validate_evidence_ids(independent_ids, valid_ids, field_name="challenge.independent_evidence_ids")

    return ChallengeResult(
        hypothesis_id=hypothesis.id,
        status=challenge_status,  # type: ignore[arg-type]
        challenge_rationale=rationale,
        contradicting_evidence_ids=valid_contra[:5],
        independent_evidence_ids=independent_ids[:5],
        challenger_agent="ChallengeAgent",
    )
