"""Deterministic Recovery Execution Simulation (Phase 5.4).

TRACEIQ NEVER performs real production remediation.
This module provides a deterministic, synthetic simulation of recovery execution.

Safety Invariants:
1. MANDATORY HUMAN APPROVAL GATE: Cannot simulate execution on unapproved actions.
2. NO REAL INFRASTRUCTURE TOUCHED (No kubectl, terraform, cloud, shell, prod DB).
3. DETERMINISTIC TELEMETRY RESTORATION based on the synthetic scenario model.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.ai.schemas import ExecutionOutcome, RecoveryExecutionSimulation

_FORBIDDEN_KEYWORDS = frozenset([
    "drop",
    "delete",
    "purge",
    "rm -rf",
    "truncate",
    "destroy",
    "format",
])


def execute_simulated_recovery(
    action: str,
    target: str,
    action_type: str | None = None,
    approval_status: str = "pending",
    recommendation_id: str = "",
) -> RecoveryExecutionSimulation:
    """Run a deterministic execution simulation for an approved recovery action.

    Raises ValueError if human approval gate is not satisfied.
    """
    rec_id = recommendation_id or str(uuid.uuid4())
    combined = f"{action} {target}".lower()

    # 1. Enforce Human Approval Gate server-side
    if approval_status != "approved":
        raise ValueError(
            f"Cannot execute recovery simulation for action in state '{approval_status}'. "
            "Mandatory human operator approval must be granted first."
        )

    # 2. Check for forbidden/destructive operations
    has_forbidden = any(
        re.search(rf"\b{re.escape(kw)}\b", combined)
        for kw in _FORBIDDEN_KEYWORDS
    )
    if has_forbidden:
        return RecoveryExecutionSimulation(
            execution_id=str(uuid.uuid4()),
            recommendation_id=rec_id,
            status="FAILED",
            simulated_action=action,
            telemetry_changes={},
            remaining_symptoms=["Execution rejected due to unsafe/destructive action parameters."],
            notes="Destructive operation blocked by safety simulation policy.",
            timestamp=datetime.now(timezone.utc),
        )

    # 3. Check for non-executable actions
    if action_type in ("NO_ACTION", "INVESTIGATE_FURTHER"):
        return RecoveryExecutionSimulation(
            execution_id=str(uuid.uuid4()),
            recommendation_id=rec_id,
            status="BLOCKED",
            simulated_action=action,
            telemetry_changes={},
            remaining_symptoms=["Investigation inconclusive; remediation not executable."],
            notes="Cannot simulate execution of an investigation or placeholder action.",
            timestamp=datetime.now(timezone.utc),
        )

    # 4. Deterministic Telemetry Synthesis based on action type / keywords
    status: ExecutionOutcome = "SUCCESS"
    remaining_symptoms: list[str] = []
    telemetry_changes: dict[str, Any] = {}
    notes: str = ""

    if action_type == "ROLLBACK_DEPLOYMENT" or "rollback" in combined:
        telemetry_changes = {
            "error_rate": "0.01% (baseline restored, down from 14.8%)",
            "p99_latency_ms": "42ms (down from 1450ms)",
            "deployment_version": "v2.4.0 (reverted from v2.4.1)",
            "service_health": "HEALTHY (10/10 pods reporting passing health checks)",
        }
        notes = f"Simulated rollback on {target} completed. Telemetry returned toward baseline within 120s."

    elif action_type == "REDUCE_DATABASE_PRESSURE" or "database" in combined or "pool" in combined or "query" in combined:
        telemetry_changes = {
            "connection_pool_saturation": "18% (down from 98%)",
            "p99_query_latency_ms": "12ms (down from 2800ms)",
            "active_connections": "36 / 200",
            "slow_query_count": "0 (down from 45/min)",
        }
        notes = f"Connection pool throttled and idle sessions terminated on {target}. Database latency normalized."

    elif action_type == "ENABLE_FALLBACK" or "dependency" in combined or "fallback" in combined:
        status = "SUCCESS"
        telemetry_changes = {
            "circuit_breaker_state": "OPEN (traffic diverted to fallback cache)",
            "client_error_rate": "0.02% (down from 18.5%)",
            "fallback_hit_rate": "99.4%",
            "outbound_timeouts": "0 / min",
        }
        remaining_symptoms = [
            "Service operating in degraded fallback mode until upstream third-party stabilizes"
        ]
        notes = f"Circuit breaker activated on {target}. Upstream dependency calls bypassed; transactions fulfilled via fallback."

    elif action_type == "RESTORE_CONFIGURATION" or "config" in combined:
        telemetry_changes = {
            "thread_pool_utilization": "22% (down from 100%)",
            "error_rate": "0.00% (down from 8.2%)",
            "queue_depth": "0 (down from 1500)",
            "config_version": "baseline-verified",
        }
        notes = f"Configuration parameters on {target} restored to baseline. Worker threads stabilized."

    else:
        # Generic safe action
        status = "SUCCESS"
        telemetry_changes = {
            "error_rate": "0.01%",
            "service_health": "HEALTHY",
            "mitigation": "applied",
        }
        notes = f"Simulated recovery action '{action}' on {target} executed successfully."

    return RecoveryExecutionSimulation(
        execution_id=str(uuid.uuid4()),
        recommendation_id=rec_id,
        status=status,
        simulated_action=action,
        telemetry_changes=telemetry_changes,
        remaining_symptoms=remaining_symptoms,
        notes=notes,
        timestamp=datetime.now(timezone.utc),
    )
