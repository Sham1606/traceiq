"""Phase 5.4 Tests — Recovery Advisor, Blast-Radius, Execution Simulation, Postmortem, Memory Archival.

Coverage:
- Service topology determinism
- Blast-radius calculation for all four scenario domains
- Human approval gate enforcement
- Execution simulation (approval required)
- Recovery advisor domain derivation per scenario
- Postmortem synthesis (evidence-grounded, no ground truth)
- Memory archival workflow
- API endpoints for all Phase 5.4 routes
- Ground truth leakage: zero
"""
from __future__ import annotations

import pytest

from app.ai.ground_truth import assert_no_ground_truth
from app.ai.schemas import BlastRadiusSimulation, RecoveryExecutionSimulation, RecoveryRecommendation, PostmortemDraft
from app.services.recovery.blast_radius import calculate_blast_radius, normalize_target_service
from app.services.recovery.execution import execute_simulated_recovery
from app.services.recovery.advisor import formulate_recovery_recommendations
from app.services.recovery.postmortem import generate_postmortem_draft
from app.services.recovery.topology import ALL_SERVICES, UPSTREAM_CALLERS, DOWNSTREAM_DEPENDENCIES


# ---------------------------------------------------------------------------
# Topology determinism
# ---------------------------------------------------------------------------

class TestTopology:
    def test_all_services_populated(self):
        assert "api-gateway" in ALL_SERVICES
        assert "order-service" in ALL_SERVICES
        assert "payment-service" in ALL_SERVICES
        assert "orders-db" in ALL_SERVICES
        assert "payments-db" in ALL_SERVICES
        assert "redis-cache" in ALL_SERVICES
        assert "payment-provider-api" in ALL_SERVICES

    def test_api_gateway_has_no_upstream_callers(self):
        assert UPSTREAM_CALLERS["api-gateway"] == []

    def test_order_service_caller_is_api_gateway(self):
        assert "api-gateway" in UPSTREAM_CALLERS["order-service"]

    def test_payments_db_has_no_downstream(self):
        assert DOWNSTREAM_DEPENDENCIES["payments-db"] == []

    def test_api_gateway_downstream_contains_services(self):
        assert "order-service" in DOWNSTREAM_DEPENDENCIES["api-gateway"]
        assert "payment-service" in DOWNSTREAM_DEPENDENCIES["api-gateway"]


# ---------------------------------------------------------------------------
# Blast-radius calculation
# ---------------------------------------------------------------------------

class TestBlastRadius:
    def test_safe_rollback_on_payment_service(self):
        blast = calculate_blast_radius(
            target="payment-service",
            action_type="ROLLBACK_DEPLOYMENT",
            action_description="Rollback deployment v4.2",
        )
        assert isinstance(blast, BlastRadiusSimulation)
        assert "payment-service" in blast.directly_affected
        assert blast.status in ("SAFE", "SAFE_WITH_WARNINGS", "HIGH_RISK")
        # All seven services accounted for
        all_mentioned = set(blast.directly_affected) | set(blast.indirectly_affected) | set(blast.unaffected_components)
        assert all_mentioned == ALL_SERVICES

    def test_database_action_raises_risk(self):
        blast = calculate_blast_radius(
            target="orders-db",
            action_type="REDUCE_DATABASE_PRESSURE",
            action_description="Reduce connection pool on orders-db",
        )
        assert blast.risk_level in ("medium", "high")
        assert "orders-db" in blast.directly_affected

    def test_fallback_on_external_dependency(self):
        blast = calculate_blast_radius(
            target="payment-provider-api",
            action_type="ENABLE_FALLBACK",
            action_description="Enable fallback circuit breaker",
        )
        assert blast.directly_affected == ["payment-provider-api"]
        # payment-service calls payment-provider-api, so it's an indirect upstream
        assert "payment-service" in blast.indirectly_affected

    def test_blocked_for_forbidden_action(self):
        blast = calculate_blast_radius(
            target="payments-db",
            action_type="REDUCE_DATABASE_PRESSURE",
            action_description="drop database payments_db",
        )
        assert blast.status == "BLOCKED"
        assert len(blast.validation_errors) > 0

    def test_no_action_returns_inconclusive(self):
        blast = calculate_blast_radius(
            target="api-gateway",
            action_type="NO_ACTION",
            action_description="Investigate further",
        )
        assert blast.status == "INCONCLUSIVE"
        assert blast.risk_level == "low"

    def test_unknown_target_returns_validation_error(self):
        blast = calculate_blast_radius(
            target="unrecognized-unknown-service-xyz",
            action_type="ROLLBACK_DEPLOYMENT",
            action_description="rollback",
        )
        assert len(blast.validation_errors) > 0

    def test_normalize_service_name_aliases(self):
        assert normalize_target_service("api-gateway") == "api-gateway"
        assert normalize_target_service("payment database") == "payments-db"
        assert normalize_target_service("orders database") == "orders-db"
        assert normalize_target_service("redis") == "redis-cache"
        assert normalize_target_service("external provider") == "payment-provider-api"

    def test_no_ground_truth_in_blast_radius(self):
        blast = calculate_blast_radius("payment-service", "ROLLBACK_DEPLOYMENT", "rollback")
        assert_no_ground_truth(blast.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Execution simulation
# ---------------------------------------------------------------------------

class TestExecutionSimulation:
    def test_requires_approval_gate(self):
        with pytest.raises(ValueError, match="approval"):
            execute_simulated_recovery(
                action="Rollback deployment",
                target="payment-service",
                action_type="ROLLBACK_DEPLOYMENT",
                approval_status="pending",
            )

    def test_rejected_action_also_blocked(self):
        with pytest.raises(ValueError, match="approval"):
            execute_simulated_recovery(
                action="Rollback",
                target="payment-service",
                approval_status="rejected",
            )

    def test_rollback_deployment_success(self):
        result = execute_simulated_recovery(
            action="Rollback deployment v4.2",
            target="payment-service",
            action_type="ROLLBACK_DEPLOYMENT",
            approval_status="approved",
        )
        assert isinstance(result, RecoveryExecutionSimulation)
        assert result.status == "SUCCESS"
        assert "error_rate" in result.telemetry_changes

    def test_database_pressure_reduction_success(self):
        result = execute_simulated_recovery(
            action="Reduce connection pool on orders-db",
            target="orders-db",
            action_type="REDUCE_DATABASE_PRESSURE",
            approval_status="approved",
        )
        assert result.status == "SUCCESS"
        telemetry_keys = set(result.telemetry_changes.keys())
        assert len(telemetry_keys) > 0

    def test_enable_fallback_success(self):
        result = execute_simulated_recovery(
            action="Enable circuit breaker on payment-service",
            target="payment-service",
            action_type="ENABLE_FALLBACK",
            approval_status="approved",
        )
        assert result.status == "SUCCESS"

    def test_restore_configuration_success(self):
        result = execute_simulated_recovery(
            action="Restore configuration parameter",
            target="api-gateway",
            action_type="RESTORE_CONFIGURATION",
            approval_status="approved",
        )
        assert result.status == "SUCCESS"

    def test_forbidden_action_returns_failed(self):
        result = execute_simulated_recovery(
            action="drop database payments",
            target="payments-db",
            action_type="REDUCE_DATABASE_PRESSURE",
            approval_status="approved",
        )
        assert result.status == "FAILED"

    def test_no_action_type_blocked(self):
        result = execute_simulated_recovery(
            action="Continue investigating",
            target="api-gateway",
            action_type="NO_ACTION",
            approval_status="approved",
        )
        assert result.status == "BLOCKED"

    def test_no_ground_truth_in_execution_result(self):
        result = execute_simulated_recovery(
            action="Rollback",
            target="payment-service",
            action_type="ROLLBACK_DEPLOYMENT",
            approval_status="approved",
        )
        assert_no_ground_truth(result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Recovery advisor — all four scenario domains
# ---------------------------------------------------------------------------

class TestRecoveryAdvisor:
    """Tests for all four synthetic scenario domains."""

    _BASE_EVIDENCE = {
        "evidence": [{"id": "ev-01", "summary": "Error rate spike", "strength": "supported"}],
        "metric_findings": [],
        "timeline_findings": [],
    }

    def _make_hyp(self, title: str, strength: str = "supported") -> dict:
        return {
            "id": "hyp-01",
            "title": title,
            "explanation": f"Explanation for {title}",
            "strength": strength,
            "supporting_evidence_ids": ["ev-01"],
            "evidence_ids": ["ev-01"],
            "contradicting_evidence_ids": [],
        }

    def test_deployment_regression_domain(self):
        hyp = self._make_hyp("Application regression introduced by a recent deployment")
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
        )
        assert len(recs) >= 1
        rec = recs[0]
        assert rec.action_type == "ROLLBACK_DEPLOYMENT"
        assert rec.risk_level in ("low", "medium", "high")

    def test_database_degradation_domain(self):
        hyp = self._make_hyp("Database performance degradation and connection pool exhaustion")
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
        )
        assert len(recs) >= 1
        rec = recs[0]
        assert rec.action_type == "REDUCE_DATABASE_PRESSURE"

    def test_external_dependency_domain(self):
        hyp = self._make_hyp("External dependency degradation causing timeout cascades")
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
        )
        assert len(recs) >= 1
        rec = recs[0]
        assert rec.action_type == "ENABLE_FALLBACK"

    def test_configuration_regression_domain(self):
        hyp = self._make_hyp("Configuration regression causing thread pool saturation")
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
        )
        assert len(recs) >= 1
        rec = recs[0]
        assert rec.action_type == "RESTORE_CONFIGURATION"

    def test_inconclusive_hypothesis_yields_investigate(self):
        hyp = self._make_hyp("Unknown root cause", strength="inconclusive")
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
        )
        assert len(recs) >= 1
        assert recs[0].action_type == "INVESTIGATE_FURTHER"

    def test_rejected_challenge_yields_investigate(self):
        hyp = self._make_hyp("Application regression introduced by a recent deployment")
        challenge = {
            "status": "rejected",
            "challenge_rationale": "Alternative explanation: database was primary cause",
            "hypothesis_id": "hyp-01",
            "contradicting_evidence_ids": ["ev-01"],
        }
        recs = formulate_recovery_recommendations(
            hypothesis=hyp,
            evidence=self._BASE_EVIDENCE,
            challenge=challenge,
        )
        assert len(recs) >= 1
        assert recs[0].action_type == "INVESTIGATE_FURTHER"

    def test_no_hypothesis_yields_inconclusive(self):
        recs = formulate_recovery_recommendations(hypothesis=None)
        assert len(recs) >= 1
        assert recs[0].action_type == "INVESTIGATE_FURTHER"

    def test_blast_radius_populated_in_recommendation(self):
        hyp = self._make_hyp("Application regression introduced by a recent deployment")
        recs = formulate_recovery_recommendations(hypothesis=hyp, evidence=self._BASE_EVIDENCE)
        rec = recs[0]
        assert rec.estimated_blast_radius is not None
        br = rec.estimated_blast_radius
        assert "status" in br
        assert "directly_affected" in br

    def test_mandatory_human_approval_in_recommendation(self):
        hyp = self._make_hyp("Application regression introduced by a recent deployment")
        recs = formulate_recovery_recommendations(hypothesis=hyp, evidence=self._BASE_EVIDENCE)
        assert all(r.requires_human_approval for r in recs)

    def test_no_ground_truth_in_recommendation(self):
        hyp = self._make_hyp("Application regression introduced by a recent deployment")
        recs = formulate_recovery_recommendations(hypothesis=hyp, evidence=self._BASE_EVIDENCE)
        for rec in recs:
            assert_no_ground_truth(rec.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Postmortem generation
# ---------------------------------------------------------------------------

class TestPostmortemGeneration:
    _BASE_INCIDENT = {
        "id": "inc-test-pm-01",
        "title": "Payment API Regression",
        "severity": "sev2",
        "scenario_id": "bad-deployment",
        "started_at": "2024-03-15T10:00:00Z",
        "detected_at": "2024-03-15T10:05:00Z",
        "recovered_at": "2024-03-15T11:00:00Z",
        "affected_services": ["api-gateway", "order-service"],
    }

    _BASE_INVESTIGATION = {
        "id": "inv-test-pm-01",
        "evidence": {
            "evidence": [{"id": "ev-01", "summary": "Error rate spike", "strength": "supported"}],
            "metric_findings": [{"metric_name": "error_rate", "service": "api-gateway", "anomaly_value": 0.14}],
            "timeline_findings": [{"timestamp": "2024-03-15T10:00:00Z", "service": "api-gateway", "description": "Error rate elevated"}],
        },
        "hypotheses": [
            {
                "id": "hyp-01",
                "title": "Application regression by recent deployment",
                "explanation": "Deployment v4.2 introduced NPE in payment handler.",
                "strength": "strongly_supported",
                "supporting_evidence_ids": ["ev-01"],
                "evidence_ids": ["ev-01"],
                "contradicting_evidence_ids": [],
            }
        ],
        "challenge": None,
    }

    def test_generates_postmortem_draft(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        assert isinstance(pm, PostmortemDraft)
        assert pm.title
        assert pm.summary
        assert pm.root_cause_analysis
        assert "hyp-01" in pm.root_cause_analysis
        assert pm.impact_duration_minutes is not None

    def test_impact_duration_calculated(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        # 10:00 to 11:00 = 60 minutes
        assert pm.impact_duration_minutes == 60.0

    def test_detected_symptoms_from_evidence(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        assert len(pm.detected_symptoms) > 0

    def test_causal_sequence_has_fact_prefix(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        fact_steps = [s for s in pm.causal_sequence if s.startswith("FACT:")]
        assert len(fact_steps) >= 1

    def test_action_items_populated(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        assert len(pm.action_items) > 0

    def test_postmortem_includes_hypothesis_id(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        assert pm.root_cause_hypothesis_id == "hyp-01"

    def test_no_ground_truth_in_postmortem(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
        )
        assert_no_ground_truth(pm.model_dump(mode="json"))

    def test_custom_notes_added_to_action_items(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
            custom_notes="Ensure on-call runbook updated for this failure mode.",
        )
        assert any("Ensure on-call runbook" in item for item in pm.action_items)

    def test_recovery_action_recorded_when_provided(self):
        pm = generate_postmortem_draft(
            incident=self._BASE_INCIDENT,
            investigation=self._BASE_INVESTIGATION,
            recovery_action={
                "action": "Rollback deployment",
                "target": "payment-service",
                "approval_status": "approved",
                "approved_by": "alice",
                "approved_at": "2024-03-15T10:45:00Z",
                "simulated_result": "partial",
                "outcome": "SUCCESS",
            },
        )
        assert pm.recovery_action_taken is not None
        assert "Rollback" in pm.recovery_action_taken


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

BASE_INCIDENT = {
    "scenario_id": "bad-deployment",
    "title": "Phase 5.4 E2E test incident",
    "severity": "sev2",
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
    "affected_services": ["api-gateway", "order-service"],
    "description": "Phase 5.4 E2E test.",
}


@pytest.fixture()
def investigation_id(client):
    r_inc = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r_inc.status_code == 201
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r_inv.status_code == 201
    return r_inv.json()["id"]


class TestPhase54APIEndpoints:
    def test_recommend_recovery_creates_actions(self, client, investigation_id):
        r = client.post(f"/api/v1/investigations/{investigation_id}/recommend-recovery")
        assert r.status_code == 201
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for action in data:
            assert action["requires_human_approval"] is True
            assert action["approval_status"] == "pending"
            assert action["simulated_result"] == "not_run"

    def test_recommended_action_has_blast_radius(self, client, investigation_id):
        r = client.post(f"/api/v1/investigations/{investigation_id}/recommend-recovery")
        assert r.status_code == 201
        actions = r.json()
        action = actions[0]
        # blast_radius should be populated in detail
        assert action.get("blast_radius") is not None or action.get("detail") is not None

    def test_blast_radius_endpoint(self, client, investigation_id):
        r_act = client.post(
            f"/api/v1/investigations/{investigation_id}/recovery-actions",
            json={
                "action": "Rollback recent deployment",
                "target": "payment-service",
                "rationale": "Deployment regression correlated with error rate spike.",
            },
        )
        assert r_act.status_code == 201
        action_id = r_act.json()["id"]

        r_br = client.post(f"/api/v1/recovery-actions/{action_id}/blast-radius")
        assert r_br.status_code == 200
        br = r_br.json()
        assert "status" in br
        assert "directly_affected" in br
        assert br["status"] in ("SAFE", "SAFE_WITH_WARNINGS", "HIGH_RISK", "BLOCKED", "INCONCLUSIVE")

    def test_execute_endpoint_requires_approval(self, client, investigation_id):
        r_act = client.post(
            f"/api/v1/investigations/{investigation_id}/recovery-actions",
            json={
                "action": "Rollback recent deployment",
                "target": "payment-service",
                "rationale": "Deployment regression.",
            },
        )
        action_id = r_act.json()["id"]
        r_exec = client.post(f"/api/v1/recovery-actions/{action_id}/execute")
        assert r_exec.status_code == 409

    def test_execute_succeeds_after_approval(self, client, investigation_id):
        r_act = client.post(
            f"/api/v1/investigations/{investigation_id}/recovery-actions",
            json={
                "action": "Rollback recent deployment",
                "target": "payment-service",
                "rationale": "Deployment regression correlated with error rate spike.",
            },
        )
        action_id = r_act.json()["id"]
        client.post(
            f"/api/v1/recovery-actions/{action_id}/approve",
            json={"approved_by": "sre-lead", "approved": True},
        )
        r_exec = client.post(f"/api/v1/recovery-actions/{action_id}/execute")
        assert r_exec.status_code == 200
        data = r_exec.json()
        assert data["outcome"] in ("SUCCESS", "PARTIAL_SUCCESS", "safe", "partial")

    def test_duplicate_approval_rejected(self, client, investigation_id):
        """H1 regression: second approval of the same action must return HTTP 409.

        Verifies:
        - First approval returns 200 and transitions to 'approved'
        - Second identical approval returns 409
        - DB state remains 'approved' — no double transition
        - Rejection is also idempotent: second reject after approve also returns 409
        """
        # Create an action in pending state
        r_act = client.post(
            f"/api/v1/investigations/{investigation_id}/recovery-actions",
            json={
                "action": "Rollback to stable release",
                "target": "payment-service",
                "rationale": "Deployment regression evidence.",
            },
        )
        assert r_act.status_code == 201
        action_id = r_act.json()["id"]
        assert r_act.json()["approval_status"] == "pending"

        # First approval — must succeed
        r_approve1 = client.post(
            f"/api/v1/recovery-actions/{action_id}/approve",
            json={"approved_by": "sre-lead", "approved": True},
        )
        assert r_approve1.status_code == 200, (
            f"First approval failed unexpectedly: {r_approve1.text}"
        )
        assert r_approve1.json()["approval_status"] == "approved"
        assert r_approve1.json()["approved_by"] == "sre-lead"

        # Second approval on the same action — must be rejected with 409
        r_approve2 = client.post(
            f"/api/v1/recovery-actions/{action_id}/approve",
            json={"approved_by": "another-operator", "approved": True},
        )
        assert r_approve2.status_code == 409, (
            f"Duplicate approval was not rejected (got {r_approve2.status_code}): {r_approve2.text}"
        )

        # DB state must remain "approved" — no override from duplicate call
        r_get = client.get(f"/api/v1/recovery-actions/{action_id}")
        assert r_get.status_code == 200
        row = r_get.json()
        assert row["approval_status"] == "approved", (
            f"Approval status corrupted to '{row['approval_status']}' after duplicate attempt"
        )
        assert row["approved_by"] == "sre-lead", (
            "approved_by was overwritten by rejected duplicate approval"
        )

        # Rejection after approval also returns 409 (no state reversion allowed)
        r_reject = client.post(
            f"/api/v1/recovery-actions/{action_id}/approve",
            json={"approved_by": "sre-lead", "approved": False},
        )
        assert r_reject.status_code == 409, (
            "Rejection of already-approved action should also return 409"
        )



    def test_postmortem_create_and_get(self, client, investigation_id):
        r_post = client.post(f"/api/v1/investigations/{investigation_id}/postmortem", json={})
        assert r_post.status_code == 201
        pm = r_post.json()
        assert "title" in pm
        assert "summary" in pm
        assert "root_cause_analysis" in pm
        assert_no_ground_truth(pm)

        r_get = client.get(f"/api/v1/investigations/{investigation_id}/postmortem")
        assert r_get.status_code == 200
        assert r_get.json()["title"] == pm["title"]

    def test_archive_memory_creates_memory_entry(self, client, investigation_id):
        r_arch = client.post(f"/api/v1/investigations/{investigation_id}/archive-memory")
        assert r_arch.status_code == 201
        mem = r_arch.json()
        assert "fingerprint" in mem
        assert mem["fingerprint"]
        assert "root_cause_category" in mem
        assert_no_ground_truth(mem)

    def test_investigation_response_includes_postmortem_field(self, client, investigation_id):
        """After postmortem generation, investigation GET must include postmortem field."""
        client.post(f"/api/v1/investigations/{investigation_id}/postmortem", json={})
        r_get = client.get(f"/api/v1/investigations/{investigation_id}")
        assert r_get.status_code == 200
        data = r_get.json()
        assert "postmortem" in data
        assert data["postmortem"] is not None
        assert_no_ground_truth(data)


# ---------------------------------------------------------------------------
# Four-scenario E2E: ground-truth leakage check on all routes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", [
    "bad-deployment",
    "database-degradation",
    "external-dependency",
    "configuration-regression",
])
class TestFourScenarioPhase54:
    def test_recommend_recovery_no_ground_truth(self, client, scenario_id: str):
        inc_payload = {
            "scenario_id": scenario_id,
            "title": f"Phase 5.4 scenario: {scenario_id}",
            "severity": "sev2",
            "started_at": "2024-03-15T10:00:00Z",
            "detected_at": "2024-03-15T10:05:00Z",
            "recovered_at": "2024-03-15T11:30:00Z",
            "affected_services": ["api-gateway"],
            "description": "Phase 5.4 test",
        }
        r_inc = client.post("/api/v1/incidents", json=inc_payload)
        assert r_inc.status_code == 201
        inc_id = r_inc.json()["id"]

        r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
        assert r_inv.status_code == 201
        assert r_inv.json()["status"] == "complete"
        inv_id = r_inv.json()["id"]

        r_rec = client.post(f"/api/v1/investigations/{inv_id}/recommend-recovery")
        assert r_rec.status_code == 201
        assert_no_ground_truth(r_rec.json())

        r_pm = client.post(f"/api/v1/investigations/{inv_id}/postmortem", json={})
        assert r_pm.status_code == 201
        assert_no_ground_truth(r_pm.json())

    def test_correct_action_type_for_scenario(self, client, scenario_id: str):
        """Verify that each scenario produces a valid, known action type from recovery advisor."""
        valid_action_types = {
            "ROLLBACK_DEPLOYMENT",
            "REDUCE_DATABASE_PRESSURE",
            "ENABLE_FALLBACK",
            "RESTORE_CONFIGURATION",
            "NO_ACTION",
            "INVESTIGATE_FURTHER",
            "SCALE_SERVICE",
            "FAILOVER",
            "DISABLE_DEPENDENCY",
        }
        inc_payload = {
            "scenario_id": scenario_id,
            "title": f"Domain type test: {scenario_id}",
            "severity": "sev2",
            "started_at": "2024-03-15T10:00:00Z",
            "detected_at": "2024-03-15T10:05:00Z",
            "recovered_at": "2024-03-15T11:30:00Z",
            "affected_services": ["api-gateway"],
            "description": "test",
        }
        r_inc = client.post("/api/v1/incidents", json=inc_payload)
        inc_id = r_inc.json()["id"]
        r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
        inv_id = r_inv.json()["id"]
        r_rec = client.post(f"/api/v1/investigations/{inv_id}/recommend-recovery")
        assert r_rec.status_code == 201
        actions = r_rec.json()
        assert len(actions) >= 1
        for action in actions:
            action_type = action.get("action_type") or (action.get("detail") or {}).get("action_type")
            if action_type:
                assert action_type in valid_action_types, (
                    f"Unknown action_type '{action_type}' for scenario {scenario_id}"
                )
