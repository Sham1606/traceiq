"""Recovery Advisor (Phase 5.4).

Formulates evidence-grounded candidate recovery recommendations from validated RCA.

Invariants:
- Ground-truth firewall protected (no hidden scenario keys allowed).
- All recommendations reference the validated hypothesis ID and supporting evidence IDs.
- Deterministic derivation authoritative; optional AI proposals strictly validated.
- Non-conclusive or rejected hypotheses yield NO_ACTION / INVESTIGATE_FURTHER.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.ai.ground_truth import assert_no_ground_truth
from app.ai.providers.base import AIProvider
from app.ai.schemas import RecoveryActionType, RecoveryRecommendation
from app.ai.validation import extract_valid_evidence_ids
from app.services.recovery.blast_radius import calculate_blast_radius, normalize_target_service

logger = logging.getLogger(__name__)


def formulate_recovery_recommendations(
    hypothesis: dict[str, Any] | None,
    evidence: dict[str, Any] | None = None,
    challenge: dict[str, Any] | None = None,
    historical_context: list[dict[str, Any]] | None = None,
    provider: AIProvider | None = None,
) -> list[RecoveryRecommendation]:
    """Propose candidate recovery actions derived from the validated hypothesis and evidence.

    AI recommends; deterministic logic validates and calculates blast radius.
    """
    # 1. Ground truth firewall validation
    if hypothesis:
        assert_no_ground_truth(hypothesis)
    if evidence:
        assert_no_ground_truth(evidence)
    if challenge:
        assert_no_ground_truth(challenge)
    if historical_context:
        assert_no_ground_truth(historical_context)

    valid_evidence_ids = extract_valid_evidence_ids(evidence or {})

    # 2. Safety check: missing or rejected hypothesis
    if not hypothesis:
        return [_build_inconclusive_recommendation("No hypothesis was provided for recovery planning.")]

    hyp_id = str(hypothesis.get("id", "hyp-unknown"))
    title = str(hypothesis.get("title", ""))
    explanation = str(hypothesis.get("explanation", ""))
    hyp_strength = str(hypothesis.get("strength", "inconclusive"))

    # If adversarial challenge rejected the leading hypothesis
    if challenge and challenge.get("status") == "rejected":
        rec_id = str(uuid.uuid4())
        rec = RecoveryRecommendation(
            recommendation_id=rec_id,
            hypothesis_id=hyp_id,
            action_type="INVESTIGATE_FURTHER",
            action_description="Suspend recovery action; gather additional telemetry to resolve challenge objections",
            target_service="incident-investigation",
            target_component="investigation-engine",
            rationale=(
                f"Leading hypothesis '{title}' was rejected during adversarial challenge: "
                f"{challenge.get('challenge_rationale', 'Alternative explanations remain unaddressed')}."
            ),
            expected_effect="Prevents premature or harmful intervention.",
            risk_level="low",
            supporting_evidence_ids=[
                eid for eid in challenge.get("contradicting_evidence_ids", [])
                if eid in valid_evidence_ids
            ],
            prerequisites=["Await further diagnostic metrics or telemetry collection"],
            rollback_plan="N/A",
            simulation_status="INCONCLUSIVE",
            approval_status="pending",
        )
        blast = calculate_blast_radius("incident-investigation", "INVESTIGATE_FURTHER", recommendation_id=rec_id)
        rec.estimated_blast_radius = blast.model_dump(mode="json")
        return [rec]

    # If hypothesis strength is inconclusive
    if hyp_strength in ("inconclusive", "rejected"):
        return [_build_inconclusive_recommendation(
            f"Leading hypothesis '{title}' is {hyp_strength}; evidence is insufficient for safe remediation.",
            hyp_id=hyp_id,
        )]

    # Gather grounded supporting evidence IDs
    hyp_supp = hypothesis.get("supporting_evidence_ids", [])
    grounded_evidence_ids = [eid for eid in hyp_supp if eid in valid_evidence_ids]
    if not grounded_evidence_ids:
        # Fall back to any referenced evidence IDs that are valid
        all_refs = hypothesis.get("evidence_ids", [])
        grounded_evidence_ids = [eid for eid in all_refs if eid in valid_evidence_ids][:5]

    # 3. Deterministic Domain Derivation
    combined_text = f"{title} {explanation}".lower()

    # Domain A: Deployment Regression
    if "deployment" in combined_text or "release" in combined_text:
        target_service = _infer_target_service(combined_text, evidence, default="payment-service")
        action_type: RecoveryActionType = "ROLLBACK_DEPLOYMENT"
        action_desc = f"Rollback deployment on {target_service} to previous verified release"
        rationale = (
            f"Validated hypothesis indicates regression introduced by recent deployment. "
            f"Reverting release on {target_service} eliminates the regression."
        )
        expected_effect = "Application error rate drops toward baseline <0.01%; service health green."
        prerequisites = [
            f"Previous stable deployment artifact for {target_service} available",
            "Health checks active",
        ]
        rollback_plan = f"Redeploy newer version or apply forward fix if rollback does not restore service."

    # Domain B: Database Degradation
    elif "database" in combined_text or " db " in combined_text or "query" in combined_text or "connection" in combined_text:
        target_service = _infer_target_service(combined_text, evidence, default="payments-db")
        action_type = "REDUCE_DATABASE_PRESSURE"
        action_desc = f"Reduce connection pool limits and terminate idle connections on {target_service}"
        rationale = (
            f"Validated hypothesis indicates database connection pool exhaustion / query degradation. "
            f"Draining idle connections and scaling pool headroom restores query throughput."
        )
        expected_effect = "Connection pool saturation drops below 25%; p99 query latency returns to normal."
        prerequisites = [
            f"Administrative connection access to {target_service}",
            "Connection pooling configuration writable",
        ]
        rollback_plan = "Restore previous connection pool configuration and restart replicas if needed."

    # Domain C: External Dependency Degradation
    elif "dependency" in combined_text or "external" in combined_text or "timeout" in combined_text:
        target_service = _infer_target_service(combined_text, evidence, default="payment-service")
        action_type = "ENABLE_FALLBACK"
        action_desc = f"Enable circuit breaker fallback routing and backoff for external dependency on {target_service}"
        rationale = (
            f"Validated hypothesis indicates external third-party API latency/failures. "
            f"Enabling circuit breaker fallback isolates service from upstream timeout cascades."
        )
        expected_effect = "External timeout errors eliminated; checkout requests handled via graceful fallback."
        prerequisites = [
            "Fallback mock/cache provider configured and available",
            "Circuit breaker threshold active",
        ]
        rollback_plan = "Disable circuit breaker and resume direct upstream calls once third-party recovers."

    # Domain D: Configuration Regression
    elif "configuration" in combined_text or "config" in combined_text:
        target_service = _infer_target_service(combined_text, evidence, default="api-gateway")
        action_type = "RESTORE_CONFIGURATION"
        action_desc = f"Restore previous configuration parameter value on {target_service}"
        rationale = (
            f"Validated hypothesis indicates service regression caused by configuration change. "
            f"Reverting parameter restores verified operating limits."
        )
        expected_effect = "Resource limits normalized; error rate drops to baseline."
        prerequisites = [
            "Configuration version history available",
            "Dynamic config reload supported",
        ]
        rollback_plan = "Re-apply modified configuration parameter if regression is determined unrelated."

    else:
        # Default fallback
        target_service = _infer_target_service(combined_text, evidence, default="api-gateway")
        action_type = "INVESTIGATE_FURTHER"
        action_desc = f"Perform deep diagnostic inspection on {target_service}"
        rationale = f"Observed symptoms on {target_service} do not cleanly map to a single high-confidence automated mitigation."
        expected_effect = "Collects targeted diagnostics without risking system disruption."
        prerequisites = ["Telemetry collection agent operational"]
        rollback_plan = "N/A"

    rec_id = str(uuid.uuid4())
    blast = calculate_blast_radius(
        target=target_service,
        action_type=action_type,
        action_description=action_desc,
        recommendation_id=rec_id,
    )

    rec = RecoveryRecommendation(
        recommendation_id=rec_id,
        hypothesis_id=hyp_id,
        action_type=action_type,
        action_description=action_desc,
        target_service=target_service,
        target_component=target_service,
        rationale=rationale,
        expected_effect=expected_effect,
        risk_level=blast.risk_level,
        supporting_evidence_ids=grounded_evidence_ids,
        prerequisites=prerequisites,
        estimated_blast_radius=blast.model_dump(mode="json"),
        rollback_plan=rollback_plan,
        simulation_status=blast.status,
        approval_status="pending",
    )

    return [rec]


def _infer_target_service(text: str, evidence: dict[str, Any] | None, default: str) -> str:
    """Deterministically extract the affected target service from text or evidence."""
    for candidate in ["payments-db", "orders-db", "payment-service", "order-service", "api-gateway", "redis-cache", "payment-provider-api"]:
        if candidate in text:
            return candidate

    if evidence:
        # Check timeline findings for service name
        timeline = evidence.get("timeline", []) or evidence.get("timeline_findings", [])
        for event in timeline:
            if isinstance(event, dict) and event.get("service"):
                norm = normalize_target_service(event["service"])
                if norm:
                    return norm

    return default


def _build_inconclusive_recommendation(rationale: str, hyp_id: str = "") -> RecoveryRecommendation:
    rec_id = str(uuid.uuid4())
    blast = calculate_blast_radius("incident-investigation", "INVESTIGATE_FURTHER", recommendation_id=rec_id)
    return RecoveryRecommendation(
        recommendation_id=rec_id,
        hypothesis_id=hyp_id or "hyp-inconclusive",
        action_type="INVESTIGATE_FURTHER",
        action_description="Gather additional telemetry before initiating recovery actions",
        target_service="incident-investigation",
        target_component="investigation-engine",
        rationale=rationale,
        expected_effect="Prevents ungrounded or hazardous remediation attempts.",
        risk_level="low",
        supporting_evidence_ids=[],
        prerequisites=["Additional diagnostic metrics collected"],
        rollback_plan="N/A",
        simulation_status="INCONCLUSIVE",
        approval_status="pending",
        estimated_blast_radius=blast.model_dump(mode="json"),
    )
