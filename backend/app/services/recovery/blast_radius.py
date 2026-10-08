"""Deterministic blast-radius simulation engine (Phase 5.4).

Answers:
"If this recovery action were executed, what could be affected?"

Calculates:
- Directly affected service
- Indirectly affected services (upstream callers and downstream dependencies)
- Unaffected services
- Risk level
- Warnings and prerequisite validations
- Rollback feasibility

This engine is 100% deterministic and never delegates blast radius to an LLM.
"""
from __future__ import annotations

import re
import uuid
from typing import Literal

from app.ai.schemas import BlastRadiusSimulation, SimulationStatus
from app.services.recovery.topology import (
    ALL_SERVICES,
    CRITICAL_SERVICES,
    get_all_downstream_dependencies,
    get_all_upstream_callers,
)

_FORBIDDEN_KEYWORDS = frozenset([
    "drop",
    "delete",
    "purge",
    "rm -rf",
    "truncate",
    "destroy",
    "format",
])


def normalize_target_service(target: str) -> str | None:
    """Resolve a user or AI target string into a known canonical service name."""
    cleaned = target.strip().lower()
    if cleaned in ALL_SERVICES:
        return cleaned

    # Substring / alias mappings
    if "api" in cleaned and "gateway" in cleaned:
        return "api-gateway"
    if "payment" in cleaned and ("db" in cleaned or "database" in cleaned):
        return "payments-db"
    if "order" in cleaned and ("db" in cleaned or "database" in cleaned):
        return "orders-db"
    if "redis" in cleaned or "cache" in cleaned:
        return "redis-cache"
    if "provider" in cleaned or "third-party" in cleaned or "external" in cleaned:
        return "payment-provider-api"
    if "payment" in cleaned:
        return "payment-service"
    if "order" in cleaned:
        return "order-service"
    if "gateway" in cleaned:
        return "api-gateway"

    # Match against ALL_SERVICES words
    for s in ALL_SERVICES:
        if s in cleaned or cleaned in s:
            return s
    return None


def calculate_blast_radius(
    target: str,
    action_type: str,
    action_description: str = "",
    recommendation_id: str = "",
) -> BlastRadiusSimulation:
    """Deterministically analyze the blast radius of a candidate recovery action."""
    rec_id = recommendation_id or str(uuid.uuid4())
    combined_text = f"{action_type} {action_description} {target}".lower()

    validation_errors: list[str] = []
    warnings: list[str] = []

    # 1. Check for forbidden/destructive actions
    has_forbidden = any(
        re.search(rf"\b{re.escape(kw)}\b", combined_text)
        for kw in _FORBIDDEN_KEYWORDS
    )
    if has_forbidden:
        validation_errors.append(
            "Destructive or catastrophic operations (drop/delete/destroy) are forbidden in TRACEIQ."
        )

    # 2. Normalize and validate target service
    canonical_target = normalize_target_service(target)
    if not canonical_target:
        validation_errors.append(
            f"Target component '{target}' does not map to a recognized service in the system topology."
        )
        canonical_target = target or "unknown-service"

    # 3. Handle non-executable actions
    if action_type in ("NO_ACTION", "INVESTIGATE_FURTHER"):
        return BlastRadiusSimulation(
            recommendation_id=rec_id,
            status="INCONCLUSIVE",
            target_service=canonical_target,
            directly_affected=[],
            indirectly_affected=[],
            unaffected_components=sorted(list(ALL_SERVICES)),
            dependency_impacts=[],
            risk_level="low",
            predicted_outcome="No recovery action simulated. Continued investigation recommended.",
            rollback_possible=True,
            warnings=["Investigation remains inconclusive; no active remediation will be executed."],
            validation_errors=[],
        )

    # 4. Topology dependency calculation
    upstream = get_all_upstream_callers(canonical_target)
    downstream = get_all_downstream_dependencies(canonical_target)

    directly_affected = [canonical_target] if canonical_target in ALL_SERVICES else []
    indirectly_set = (set(upstream) | set(downstream)) - set(directly_affected)
    indirectly_affected = sorted(list(indirectly_set))
    unaffected = sorted(list(ALL_SERVICES - set(directly_affected) - set(indirectly_affected)))

    # 5. Dependency impacts description
    dependency_impacts: list[str] = []
    if upstream:
        dependency_impacts.append(f"Upstream callers ({', '.join(upstream)}) may experience brief retry bursts.")
    if downstream:
        dependency_impacts.append(f"Downstream dependencies ({', '.join(downstream)}) will receive recovery traffic.")

    # 6. Risk Level determination
    risk_level: Literal["low", "medium", "high"] = "medium"
    if has_forbidden or canonical_target in CRITICAL_SERVICES or action_type in ("REDUCE_DATABASE_PRESSURE", "FAILOVER"):
        risk_level = "high"
    elif action_type == "RESTORE_CONFIGURATION" and canonical_target not in CRITICAL_SERVICES and len(indirectly_affected) <= 1:
        risk_level = "low"

    # 7. Warnings
    if "api-gateway" in indirectly_affected:
        warnings.append("API Gateway is upstream; external clients may observe brief transient latency.")
    if canonical_target in CRITICAL_SERVICES:
        warnings.append(f"Target '{canonical_target}' is a critical tier component; operator verification required.")
    if not upstream and canonical_target != "api-gateway":
        warnings.append("Component has no known upstream callers in topology.")

    # 8. Status determination
    status: SimulationStatus = "SAFE"
    if validation_errors:
        status = "BLOCKED"
    elif risk_level == "high":
        status = "HIGH_RISK"
    elif warnings:
        status = "SAFE_WITH_WARNINGS"
    else:
        status = "SAFE"

    # 9. Rollback feasibility & predicted outcome
    rollback_possible = not has_forbidden and action_type != "FAILOVER"
    predicted_outcome = (
        f"Simulating {action_type} on {canonical_target}. "
        f"Direct impact confined to {canonical_target}; "
        f"{len(indirectly_affected)} indirect dependencies evaluated. "
        f"Telemetry restoration projected."
    )

    return BlastRadiusSimulation(
        recommendation_id=rec_id,
        status=status,
        target_service=canonical_target,
        directly_affected=directly_affected,
        indirectly_affected=indirectly_affected,
        unaffected_components=unaffected,
        dependency_impacts=dependency_impacts,
        risk_level=risk_level,
        predicted_outcome=predicted_outcome,
        rollback_possible=rollback_possible,
        warnings=warnings,
        validation_errors=validation_errors,
    )
