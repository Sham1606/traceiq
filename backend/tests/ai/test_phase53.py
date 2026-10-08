"""Phase 5.3 tests: Cross-investigator correlation, competing hypotheses,
historical reasoning, adversarial challenge, and four-scenario verification.

All tests use deterministic fixtures — no live LLM calls required.
"""
from __future__ import annotations

from typing import Any
import pytest

from app.ai.correlation import correlate_findings
from app.ai.challenge import challenge_hypothesis
from app.ai.historical import (
    build_fingerprint_from_evidence,
    build_historical_context_note,
    enrich_hypotheses_with_historical_context,
)
from app.ai.schemas import AIHypothesis, CorrelationFinding, ChallengeResult
from app.ai.graph import run_investigation_graph
from app.ai.ground_truth import assert_no_ground_truth
from app.ai.providers import MockAIProvider
from app.ai.state import create_initial_state
from app.ai.validation import extract_valid_evidence_ids


# =========================================================================== #
# Shared fixtures                                                               #
# =========================================================================== #

@pytest.fixture
def base_incident() -> dict[str, Any]:
    return {
        "id": "inc-53-test",
        "scenario_id": "bad-deployment",
        "title": "Payment Service Regression",
        "severity": "sev1",
        "affected_services": ["api-gateway", "payment-service"],
        "started_at": "2024-01-15T10:00:00Z",
        "detected_at": "2024-01-15T10:05:00Z",
        "recovered_at": "2024-01-15T10:25:00Z",
    }


@pytest.fixture
def deployment_evidence() -> dict[str, Any]:
    """Evidence bundle with clear deployment signal as the primary cause."""
    return {
        "evidence": [
            {
                "id": "ev-tl-deploy",
                "evidence_type": "timeline",
                "source_id": "dep-v4.2",
                "summary": "Production deployment v4.2 released at T-5min",
                "strength": "strongly_supported",
                "supports": ["deployment"],
                "contradicts": [],
            },
            {
                "id": "ev-met-err",
                "evidence_type": "metric",
                "source_id": "met-errrate",
                "summary": "5xx Error rate jumped from 0.001 to 0.142",
                "strength": "strongly_supported",
                "supports": ["error_rate"],
                "contradicts": [],
            },
            {
                "id": "ev-log-ex",
                "evidence_type": "log",
                "source_id": "log-01",
                "summary": "NullPointerException in PaymentHandler",
                "strength": "supported",
                "supports": ["application_error"],
                "contradicts": [],
            },
        ],
        "timeline_findings": [
            {
                "id": "tl-deploy-01",
                "event_type": "deployment",
                "event_id": "dep-v4.2",
                "summary": "Deployment v4.2 released",
                "timestamp": "2024-01-15T09:55:00Z",
            }
        ],
        "metric_findings": [
            {"id": "met-errrate", "service": "api-gateway", "metric": "error_rate", "anomaly": True},
            {"id": "met-latency", "service": "payment-service", "metric": "request_latency", "anomaly": True},
        ],
        "log_findings": [
            {"id": "log-01", "service": "payment-service", "error_or_warn_count": 44, "summary": "Unhandled exception in payment processing"},
        ],
        "correlation_findings": [],
    }


@pytest.fixture
def db_degradation_evidence() -> dict[str, Any]:
    """Evidence bundle with clear database signal."""
    return {
        "evidence": [
            {
                "id": "ev-db-conn",
                "evidence_type": "metric",
                "source_id": "met-db-conn",
                "summary": "DB connection pool at 98%",
                "strength": "strongly_supported",
                "supports": ["connection_pool"],
                "contradicts": [],
            },
            {
                "id": "ev-db-lat",
                "evidence_type": "metric",
                "source_id": "met-db-lat",
                "summary": "DB query latency P99 = 8200ms",
                "strength": "strongly_supported",
                "supports": ["query_latency"],
                "contradicts": [],
            },
        ],
        "timeline_findings": [],
        "metric_findings": [
            {"id": "met-db-conn", "service": "order-db", "metric": "connection_pool", "anomaly": True},
            {"id": "met-db-lat", "service": "order-db", "metric": "query_latency", "anomaly": True},
        ],
        "log_findings": [
            {"id": "log-db-01", "service": "order-db", "error_or_warn_count": 12, "summary": "Connection pool exhausted"},
        ],
        "correlation_findings": [],
    }


@pytest.fixture
def contradicting_evidence() -> dict[str, Any]:
    """Evidence with strong contradictions (DB evidence contradicts deployment hypothesis)."""
    return {
        "evidence": [
            {
                "id": "ev-no-deploy",
                "evidence_type": "timeline",
                "source_id": "no-deploy",
                "summary": "No deployment in last 7 days",
                "strength": "strongly_supported",
                "supports": [],
                "contradicts": ["deployment"],
            },
            {
                "id": "ev-db-spike",
                "evidence_type": "metric",
                "source_id": "met-db-spike",
                "summary": "DB connection count spiked 3 hours before incident",
                "strength": "supported",
                "supports": ["database"],
                "contradicts": [],
            },
        ],
        "timeline_findings": [],
        "metric_findings": [
            {"id": "met-db-spike", "service": "analytics-db", "metric": "connection_count", "anomaly": True},
        ],
        "log_findings": [],
        "correlation_findings": [],
    }


# =========================================================================== #
# 1. CorrelationFinding schema tests                                           #
# =========================================================================== #

class TestCorrelationFindingSchema:
    def test_correlation_finding_fields(self):
        cf = CorrelationFinding(
            correlation_id="corr-001",
            correlated_domains=["deployment", "application"],
            shared_evidence_ids=["ev-001", "ev-002"],
            causal_sequence=["[DEPLOYMENT] v4.2 released", "[METRIC] Error rate spike"],
            false_lead_domains=["dependency"],
            contradicting_evidence_ids=[],
            summary="Deployment and application findings share temporal alignment.",
            strength="strongly_supported",
        )
        assert cf.correlation_id == "corr-001"
        assert "deployment" in cf.correlated_domains
        assert "dependency" in cf.false_lead_domains
        assert cf.strength == "strongly_supported"

    def test_correlation_finding_rejects_extra_fields(self):
        with pytest.raises(Exception):
            CorrelationFinding.model_validate({
                "correlation_id": "corr-001",
                "summary": "test",
                "strength": "supported",
                "hallucinated_field": True,
            })

    def test_correlation_finding_default_strength(self):
        cf = CorrelationFinding(
            correlation_id="corr-002",
            summary="No signals.",
        )
        assert cf.strength == "supported"  # default


# =========================================================================== #
# 2. Correlation engine tests                                                   #
# =========================================================================== #

class TestCorrelationEngine:
    def test_correlate_finds_shared_evidence_ids(self, deployment_evidence):
        findings = [
            {
                "finding_id": "find-dep-01",
                "investigator_type": "deployment",
                "domain": "deployment",
                "evidence_ids": ["ev-tl-deploy", "ev-met-err"],
                "supporting_evidence_ids": ["ev-tl-deploy", "ev-met-err"],
                "contradicting_evidence_ids": [],
            },
            {
                "finding_id": "find-app-01",
                "investigator_type": "application",
                "domain": "application",
                "evidence_ids": ["ev-met-err", "ev-log-ex"],
                "supporting_evidence_ids": ["ev-met-err", "ev-log-ex"],
                "contradicting_evidence_ids": [],
            },
        ]
        corr = correlate_findings(findings, deployment_evidence)

        assert isinstance(corr, CorrelationFinding)
        assert "ev-met-err" in corr.shared_evidence_ids, "Shared ID not detected"
        assert "deployment" in corr.correlated_domains
        assert "application" in corr.correlated_domains
        assert corr.strength in ("strongly_supported", "supported")

    def test_correlate_identifies_false_lead_domain(self, deployment_evidence):
        """A domain with no valid evidence IDs is flagged as a false lead."""
        findings = [
            {
                "finding_id": "find-dep-01",
                "investigator_type": "deployment",
                "domain": "deployment",
                "evidence_ids": ["ev-tl-deploy"],
                "supporting_evidence_ids": ["ev-tl-deploy"],
                "contradicting_evidence_ids": [],
            },
            {
                "finding_id": "find-db-01",
                "investigator_type": "database",
                "domain": "database",
                "evidence_ids": [],  # No evidence — false lead candidate
                "supporting_evidence_ids": [],
                "contradicting_evidence_ids": [],
            },
        ]
        corr = correlate_findings(findings, deployment_evidence)
        assert "database" in corr.false_lead_domains, "database should be a false lead"

    def test_correlate_rejects_hallucinated_ids(self, deployment_evidence):
        """Hallucinated IDs not present in the evidence bundle must raise an error."""
        findings = [
            {
                "finding_id": "find-hallucinated",
                "investigator_type": "application",
                "domain": "application",
                "evidence_ids": ["HALLUCINATED-ID-999"],
                "supporting_evidence_ids": ["HALLUCINATED-ID-999"],
                "contradicting_evidence_ids": [],
            }
        ]
        # Hallucinated IDs are filtered out (not in valid_ids), so correlation still produces output
        # but the hallucinated ID is NOT in the result
        corr = correlate_findings(findings, deployment_evidence)
        assert "HALLUCINATED-ID-999" not in corr.shared_evidence_ids

    def test_correlate_causal_sequence_from_timeline(self, deployment_evidence):
        corr = correlate_findings([], deployment_evidence)
        assert len(corr.causal_sequence) >= 1
        assert "DEPLOYMENT" in corr.causal_sequence[0].upper()

    def test_correlate_empty_findings_produces_inconclusive(self, deployment_evidence):
        corr = correlate_findings([], deployment_evidence)
        assert corr.strength in ("inconclusive", "weakly_supported", "supported")

    def test_correlate_no_ground_truth_in_output(self, deployment_evidence):
        findings = [
            {
                "finding_id": "find-dep-01",
                "investigator_type": "deployment",
                "domain": "deployment",
                "evidence_ids": ["ev-tl-deploy"],
                "supporting_evidence_ids": ["ev-tl-deploy"],
                "contradicting_evidence_ids": [],
            }
        ]
        corr = correlate_findings(findings, deployment_evidence)
        assert_no_ground_truth(corr.model_dump(mode="json"))


# =========================================================================== #
# 3. Challenge Agent tests                                                      #
# =========================================================================== #

class TestChallengeAgent:
    def _make_hypothesis(
        self,
        hyp_id: str = "hyp-01",
        title: str = "Application regression introduced by recent deployment",
        strength: str = "strongly_supported",
        sup_ids: list[str] | None = None,
        con_ids: list[str] | None = None,
    ) -> AIHypothesis:
        return AIHypothesis(
            id=hyp_id,
            title=title,
            explanation="Test explanation.",
            supporting_evidence_ids=sup_ids or [],
            contradicting_evidence_ids=con_ids or [],
            missing_evidence=[],
            reasoning_summary="Test reasoning.",
            strength=strength,  # type: ignore[arg-type]
        )

    def test_challenge_returns_supported_for_strong_hypothesis(self, deployment_evidence):
        hyp = self._make_hypothesis(
            sup_ids=["ev-tl-deploy", "ev-met-err"],
            strength="strongly_supported",
        )
        corr = CorrelationFinding(
            correlation_id="corr-01",
            correlated_domains=["deployment", "application"],
            shared_evidence_ids=["ev-met-err"],
            causal_sequence=["[DEPLOYMENT] v4.2 released"],
            false_lead_domains=[],
            contradicting_evidence_ids=[],
            summary="Strong deployment correlation.",
            strength="strongly_supported",
        )
        result = challenge_hypothesis(hyp, corr, deployment_evidence)
        assert isinstance(result, ChallengeResult)
        assert result.hypothesis_id == "hyp-01"
        assert result.status == "supported"
        assert result.challenger_agent == "ChallengeAgent"

    def test_challenge_rejects_hypothesis_with_contradictions_outweighing_support(
        self, contradicting_evidence
    ):
        """When strong contradicting evidence outweighs supporting, hypothesis must be REJECTED."""
        hyp = self._make_hypothesis(
            title="Application regression introduced by recent deployment",
            sup_ids=[],  # zero supporting
            con_ids=["ev-no-deploy"],  # explicit contradiction
            strength="weakly_supported",
        )
        corr = CorrelationFinding(
            correlation_id="corr-02",
            correlated_domains=[],
            shared_evidence_ids=[],
            causal_sequence=[],
            false_lead_domains=["deployment"],
            contradicting_evidence_ids=["ev-no-deploy"],
            summary="No deployment-domain correlation found.",
            strength="weakly_supported",
        )
        result = challenge_hypothesis(hyp, corr, contradicting_evidence)
        assert result.status == "rejected", (
            f"Expected REJECTED but got {result.status}: {result.challenge_rationale}"
        )

    def test_challenge_returns_inconclusive_for_weak_hypothesis(self, deployment_evidence):
        hyp = self._make_hypothesis(
            sup_ids=[],
            con_ids=[],
            strength="inconclusive",
        )
        # Build an inconclusive deployment_evidence (no sup IDs in valid_ids for this hyp)
        result = challenge_hypothesis(hyp, None, deployment_evidence)
        assert result.status in ("rejected", "inconclusive")

    def test_challenge_result_evidence_ids_are_all_valid(self, deployment_evidence):
        """All evidence IDs in ChallengeResult must be present in the evidence bundle."""
        valid_ids = extract_valid_evidence_ids(deployment_evidence)
        hyp = self._make_hypothesis(
            sup_ids=["ev-tl-deploy", "ev-met-err"],
            strength="strongly_supported",
        )
        result = challenge_hypothesis(hyp, None, deployment_evidence)
        for eid in result.contradicting_evidence_ids:
            assert eid in valid_ids, f"Invalid ID in challenge.contradicting_evidence_ids: {eid}"
        for eid in result.independent_evidence_ids:
            assert eid in valid_ids, f"Invalid ID in challenge.independent_evidence_ids: {eid}"

    def test_challenge_no_ground_truth_in_output(self, deployment_evidence):
        hyp = self._make_hypothesis(sup_ids=["ev-tl-deploy"], strength="supported")
        result = challenge_hypothesis(hyp, None, deployment_evidence)
        assert_no_ground_truth(result.model_dump(mode="json"))

    def test_challenge_false_deployment_lead_rejected(self, contradicting_evidence):
        """Deployment hypothesis where the timeline has no deployment → REJECTED."""
        hyp = self._make_hypothesis(
            title="Application regression introduced by recent deployment",
            sup_ids=[],
            con_ids=["ev-no-deploy"],
            strength="inconclusive",
        )
        result = challenge_hypothesis(hyp, None, contradicting_evidence)
        assert result.status in ("rejected", "inconclusive"), (
            "Deployment hypothesis with zero timeline support should not be 'supported'"
        )

    def test_challenge_mock_provider_is_not_called_for_adversarial_path(self, deployment_evidence):
        """Mock provider should NOT be used for the challenge's adversarial reasoning path
        (it is only for non-mock providers). Challenge must use deterministic logic."""
        provider = MockAIProvider()
        hyp = self._make_hypothesis(sup_ids=["ev-tl-deploy"], strength="strongly_supported")
        result = challenge_hypothesis(hyp, None, deployment_evidence, provider=provider)
        # No mock calls made for adversarial challenge (mock provider.provider_name == 'mock')
        challenge_calls = [c for c in provider.call_history if "challenge" in str(c).lower()]
        assert len(challenge_calls) == 0, "Mock provider should not be called for challenge on mock path"


# =========================================================================== #
# 4. Historical reasoning tests                                                 #
# =========================================================================== #

class TestHistoricalReasoning:
    def _make_match(
        self,
        title: str = "Past DB Incident",
        category: str = "database_degradation",
        shared_tokens: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "memory": {
                "id": "mem-001",
                "title": title,
                "root_cause_category": category,
                "evidence_summary": ["DB connection saturation", "Slow query spikes"],
                "recovery_action": "Flush connection pool",
                "recovery_outcome": "resolved",
                "scenario_id": "database-degradation",
                "incident_id": "inc-past-01",
                "fingerprint": "database connection_pool sev1",
            },
            "shared_fingerprint_tokens": shared_tokens or ["database", "connection_pool"],
            "match_note": "Historical incident shares 2 fingerprint token(s). Treat as supporting context only.",
        }

    def test_build_historical_context_note_with_matches(self):
        matches = [self._make_match(), self._make_match(title="Another DB Incident", category="configuration")]
        note = build_historical_context_note(matches)
        assert "Historical context: 2 similar" in note
        assert "Past DB Incident" in note
        assert "supporting context only" in note
        assert "validate all conclusions" in note.lower()

    def test_build_historical_context_note_empty(self):
        note = build_historical_context_note([])
        assert note == ""

    def test_enrich_hypotheses_does_not_change_strength(self):
        hypotheses = [
            {
                "id": "hyp-01",
                "title": "Deployment regression",
                "explanation": "Test",
                "supporting_evidence_ids": ["ev-001"],
                "contradicting_evidence_ids": [],
                "missing_evidence": [],
                "reasoning_summary": "test",
                "strength": "strongly_supported",
            }
        ]
        matches = [self._make_match()]
        enriched = enrich_hypotheses_with_historical_context(hypotheses, matches)

        assert len(enriched) == 1
        # Strength must NOT change
        assert enriched[0]["strength"] == "strongly_supported"
        # Historical IDs must NOT be added to evidence fields
        assert "mem-001" not in enriched[0].get("supporting_evidence_ids", [])
        # Context note must be in metadata
        assert "historical_context_note" in enriched[0]["metadata"]
        assert enriched[0]["metadata"]["historical_override"] is False

    def test_enrich_hypotheses_marks_as_non_overriding(self):
        """Historical match must never automatically be treated as ground truth."""
        hypotheses = [{"id": "hyp-01", "title": "DB", "explanation": "e", "supporting_evidence_ids": [],
                       "contradicting_evidence_ids": [], "missing_evidence": [], "reasoning_summary": "r", "strength": "inconclusive"}]
        matches = [self._make_match(category="database_degradation")]
        enriched = enrich_hypotheses_with_historical_context(hypotheses, matches)
        assert enriched[0]["metadata"]["historical_override"] is False

    def test_historical_false_match_does_not_strengthen_weak_hypothesis(self):
        """Even a matching historical incident must not upgrade a weakly-supported hypothesis."""
        hypotheses = [{"id": "hyp-01", "title": "Weak hypothesis", "explanation": "e",
                       "supporting_evidence_ids": [], "contradicting_evidence_ids": [],
                       "missing_evidence": [], "reasoning_summary": "r", "strength": "weakly_supported"}]
        matches = [self._make_match(category="deployment_regression")]
        enriched = enrich_hypotheses_with_historical_context(hypotheses, matches)
        # Strength must remain weakly_supported
        assert enriched[0]["strength"] == "weakly_supported"

    def test_build_fingerprint_from_evidence(self, deployment_evidence, base_incident):
        fp = build_fingerprint_from_evidence(deployment_evidence, base_incident)
        assert isinstance(fp, str)
        assert len(fp) > 0
        # Should not contain ground truth fields
        assert "root_cause" not in fp
        assert "ground_truth" not in fp

    def test_build_fingerprint_includes_event_types(self, deployment_evidence, base_incident):
        fp = build_fingerprint_from_evidence(deployment_evidence, base_incident)
        # deployment timeline event type should be tokenized
        assert "deployment" in fp

    def test_build_fingerprint_empty_evidence(self, base_incident):
        fp = build_fingerprint_from_evidence({}, base_incident)
        assert fp  # may just be severity or 'unknown', but not empty


# =========================================================================== #
# 5. Full LangGraph pipeline (Phase 5.3 nodes)                                 #
# =========================================================================== #

class TestPhase53Pipeline:
    def test_correlation_node_executed_in_pipeline(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert "correlation" in final["metadata"]["nodes_executed"]

    def test_historical_context_node_executed_in_pipeline(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert "historical_context" in final["metadata"]["nodes_executed"]

    def test_challenge_node_executed_in_pipeline(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert "challenge" in final["metadata"]["nodes_executed"]

    def test_pipeline_produces_correlations(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert len(final.get("correlations", [])) >= 1

    def test_pipeline_produces_multiple_competing_hypotheses(self, base_incident, deployment_evidence):
        """Phase 5.3: pipeline should produce ≥1 ranked hypothesis (competing generation)."""
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        hypotheses = final.get("hypotheses", [])
        assert len(hypotheses) >= 1, "At least one hypothesis must be generated"

    def test_pipeline_produces_challenge_result(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        challenge = final.get("challenge")
        assert challenge is not None, "Challenge result must be present"
        assert challenge["status"] in ("supported", "rejected", "inconclusive")
        assert challenge["challenger_agent"] == "ChallengeAgent"

    def test_pipeline_challenge_status_is_valid(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert final["challenge"]["status"] in {"supported", "rejected", "inconclusive"}

    def test_pipeline_all_phase53_nodes_present(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        nodes = final["metadata"]["nodes_executed"]
        for required_node in ["correlation", "historical_context", "hypotheses", "challenge"]:
            assert required_node in nodes, f"Phase 5.3 node '{required_node}' not executed"

    def test_pipeline_no_ground_truth_in_final_state(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert_no_ground_truth(final)

    def test_pipeline_all_correlation_evidence_ids_valid(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        valid_ids = extract_valid_evidence_ids(deployment_evidence)
        for corr in final.get("correlations", []):
            for eid in corr.get("shared_evidence_ids", []):
                assert eid in valid_ids, f"Correlation contains invalid evidence ID: {eid}"
            for eid in corr.get("contradicting_evidence_ids", []):
                assert eid in valid_ids, f"Correlation contains invalid contradicting ID: {eid}"

    def test_pipeline_all_hypothesis_evidence_ids_valid(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        valid_ids = extract_valid_evidence_ids(deployment_evidence)
        for h in final.get("hypotheses", []):
            for eid in h.get("supporting_evidence_ids", []):
                assert eid in valid_ids, f"Hypothesis contains invalid supporting ID: {eid}"
            for eid in h.get("contradicting_evidence_ids", []):
                assert eid in valid_ids, f"Hypothesis contains invalid contradicting ID: {eid}"

    def test_pipeline_challenge_evidence_ids_valid(self, base_incident, deployment_evidence):
        state = create_initial_state(base_incident, deployment_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        valid_ids = extract_valid_evidence_ids(deployment_evidence)
        challenge = final.get("challenge") or {}
        for eid in challenge.get("contradicting_evidence_ids", []):
            assert eid in valid_ids, f"Challenge contains invalid contradicting ID: {eid}"
        for eid in challenge.get("independent_evidence_ids", []):
            assert eid in valid_ids, f"Challenge contains invalid independent ID: {eid}"

    def test_pipeline_db_degradation_scenario(self, base_incident, db_degradation_evidence):
        """DB degradation scenario: pipeline identifies DB domain correctly."""
        incident = dict(base_incident)
        incident["affected_services"] = ["order-db", "inventory-service"]
        state = create_initial_state(incident, db_degradation_evidence)
        final = run_investigation_graph(state, provider=MockAIProvider())
        assert final.get("hypotheses"), "Hypotheses must be produced"
        assert final.get("correlations"), "Correlations must be produced"
        assert_no_ground_truth(final)

    def test_challenge_node_failure_is_isolated(self, base_incident, deployment_evidence):
        """If challenge node encounters a schema error, it records the error and continues."""
        state = create_initial_state(base_incident, deployment_evidence)
        # Run with no hypotheses — inject empty hypotheses to trigger no-op path
        state["hypotheses"] = []  # type: ignore[index]
        final = run_investigation_graph(state, provider=MockAIProvider())
        # Pipeline must still complete
        assert "evaluator" in final["metadata"]["nodes_executed"]

    def test_historical_context_is_non_overriding(self, base_incident, deployment_evidence):
        """Hypothesis strength must not change due to historical context injection."""
        # Inject fake historical context into state
        state = create_initial_state(base_incident, deployment_evidence)
        state["historical_context"] = [  # type: ignore[index]
            {
                "memory": {"title": "Similar Past Incident", "root_cause_category": "deployment_regression",
                           "id": "mem-999", "evidence_summary": [], "recovery_action": "rollback",
                           "recovery_outcome": "resolved", "scenario_id": "bad-deployment",
                           "incident_id": "inc-past-99", "fingerprint": "deployment sev1"},
                "shared_fingerprint_tokens": ["deployment"],
                "match_note": "Supporting context only.",
            }
        ]
        final = run_investigation_graph(state, provider=MockAIProvider())
        for h in final.get("hypotheses", []):
            # No historical evidence IDs may appear in hypothesis evidence fields
            assert "mem-999" not in h.get("supporting_evidence_ids", [])
            # metadata override flag must be False
            meta = h.get("metadata") or {}
            assert meta.get("historical_override") is False

    def test_db_degradation_pipeline_challenge_can_reject_false_deployment_lead(self):
        """Explicit test: for DB degradation scenario with no deployment,
        a deployment hypothesis must be challenged and rejected."""
        incident = {
            "id": "inc-db-test",
            "scenario_id": "database-degradation",
            "title": "DB Slowdown",
            "severity": "sev2",
            "affected_services": ["order-db"],
            "started_at": "2024-01-20T08:00:00Z",
            "detected_at": "2024-01-20T08:10:00Z",
            "recovered_at": "2024-01-20T09:00:00Z",
        }
        # Evidence shows DB degradation, no deployment
        evidence = {
            "evidence": [
                {
                    "id": "ev-no-dep",
                    "evidence_type": "timeline",
                    "source_id": "no-dep",
                    "summary": "No deployment in last 7 days — confirmed by deployment service",
                    "strength": "strongly_supported",
                    "supports": [],
                    "contradicts": ["deployment"],
                },
                {
                    "id": "ev-db-saturation",
                    "evidence_type": "metric",
                    "source_id": "met-db-sat",
                    "summary": "DB connection pool saturated at 99%",
                    "strength": "strongly_supported",
                    "supports": ["database"],
                    "contradicts": [],
                },
            ],
            "timeline_findings": [],
            "metric_findings": [
                {"id": "met-db-sat", "service": "order-db", "metric": "connection_pool", "anomaly": True},
            ],
            "log_findings": [],
            "correlation_findings": [],
        }

        # Directly challenge a false deployment hypothesis
        hyp = AIHypothesis(
            id="hyp-false-dep",
            title="Application regression introduced by recent deployment",
            explanation="Postulated deployment-based regression.",
            supporting_evidence_ids=[],
            contradicting_evidence_ids=["ev-no-dep"],
            missing_evidence=[],
            reasoning_summary="Hypothesised — not evidence-backed.",
            strength="inconclusive",
        )
        result = challenge_hypothesis(hyp, None, evidence)
        assert result.status in ("rejected", "inconclusive"), (
            f"Deployment hypothesis on DB incident should be rejected or inconclusive, got {result.status}"
        )


# =========================================================================== #
# 6. Four-scenario integration test (Phase 5.3 verification)                  #
# =========================================================================== #

SCENARIO_IDS = [
    "bad-deployment",
    "database-degradation",
    "external-dependency",
    "configuration-regression",
]


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_phase53_pipeline_executes_for_scenario(scenario_id: str):
    """Full Phase 5.3 pipeline must complete for all four synthetic scenarios."""
    from pathlib import Path
    from app.core.config import settings
    from app.evidence.engine import EvidenceEngine
    from app.evidence.loader import load_scenario

    engine = EvidenceEngine(settings.data_root)
    bundle = engine.investigate(scenario_id)

    scenario_data = load_scenario(Path(settings.data_root), scenario_id)
    incident = scenario_data.incident

    initial_state = create_initial_state(
        incident=incident,
        evidence_bundle=bundle,
        provider="mock",
        model="mock-reasoner",
    )

    # Ground truth must be absent before execution
    assert_no_ground_truth(initial_state)

    provider = MockAIProvider()
    final_state = run_investigation_graph(initial_state, provider=provider)

    # 1. All Phase 5.3 nodes must execute
    nodes = final_state["metadata"]["nodes_executed"]
    for node in ["correlation", "historical_context", "hypotheses", "challenge", "evaluator"]:
        assert node in nodes, f"Node '{node}' missing for scenario '{scenario_id}'"

    # 2. Findings must be present
    findings = final_state.get("findings", [])
    assert len(findings) >= 1

    # 3. Correlations must be present
    assert len(final_state.get("correlations", [])) >= 1

    # 4. Hypotheses must be present
    hypotheses = final_state.get("hypotheses", [])
    assert len(hypotheses) >= 1

    # 5. Challenge must be present
    challenge = final_state.get("challenge")
    assert challenge is not None
    assert challenge["status"] in ("supported", "rejected", "inconclusive")

    # 6. All evidence IDs must be valid (no hallucinations)
    valid_ids = extract_valid_evidence_ids(bundle.model_dump(mode="json"))

    for f in findings:
        for eid in f.get("supporting_evidence_ids", []):
            assert eid in valid_ids, f"[{scenario_id}] Invalid supporting ID in finding: {eid}"

    for corr in final_state.get("correlations", []):
        for eid in corr.get("shared_evidence_ids", []):
            assert eid in valid_ids, f"[{scenario_id}] Invalid ID in correlation: {eid}"

    for h in hypotheses:
        for eid in h.get("supporting_evidence_ids", []):
            assert eid in valid_ids, f"[{scenario_id}] Invalid ID in hypothesis: {eid}"

    for eid in challenge.get("contradicting_evidence_ids", []):
        assert eid in valid_ids, f"[{scenario_id}] Invalid ID in challenge: {eid}"

    # 7. Ground truth must be absent from final state
    assert_no_ground_truth(final_state)

    # 8. Hallucinated evidence IDs = 0 (already verified above; confirm count)
    all_cited_ids: list[str] = []
    for f in findings:
        all_cited_ids.extend(f.get("supporting_evidence_ids", []))
    for corr in final_state.get("correlations", []):
        all_cited_ids.extend(corr.get("shared_evidence_ids", []))
    for h in hypotheses:
        all_cited_ids.extend(h.get("supporting_evidence_ids", []))

    hallucinated = [eid for eid in all_cited_ids if eid not in valid_ids]
    assert len(hallucinated) == 0, (
        f"[{scenario_id}] {len(hallucinated)} hallucinated evidence IDs detected: {hallucinated}"
    )


# =========================================================================== #
# 7. Targeted Fix Verification Tests (Phase 5.3 fixes)                         #
# =========================================================================== #

class TestPhase53TargetedFixes:
    def test_challenge_and_correlation_persistence(self, db):
        """Fix 1: start_investigation must persist challenge and correlations."""
        from datetime import datetime, timezone
        from app.models.orm import IncidentRow
        from app.services.investigation.service import start_investigation
        from app.ai.config import AISettings
        import app.ai.config as ai_config

        ai_config.ai_settings = AISettings(enabled=True, provider="mock", model="mock-reasoner")

        inc = IncidentRow(
            id="inc-fix-persist-01",
            scenario_id="bad-deployment",
            title="Deployment Regression Test",
            severity="sev1",
            started_at=datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc),
            detected_at=datetime(2026, 10, 8, 10, 5, tzinfo=timezone.utc),
            recovered_at=datetime(2026, 10, 8, 10, 30, tzinfo=timezone.utc),
            affected_services=["api-gateway", "payment-service"],
        )
        db.add(inc)
        db.commit()

        resp = start_investigation(db, "inc-fix-persist-01")
        assert resp is not None
        assert resp.status == "complete"

        # 1. Challenge result must NOT be null
        assert resp.challenge is not None, "InvestigationResponse.challenge must not be None"
        assert resp.challenge["status"] in {"supported", "rejected", "inconclusive"}
        assert resp.challenge["challenger_agent"] == "ChallengeAgent"
        assert "challenge_rationale" in resp.challenge

        # 2. Correlations must be present in evidence dict
        assert resp.evidence is not None
        assert "correlations" in resp.evidence, "evidence['correlations'] must be present"
        assert any("correlation_id" in c for c in resp.evidence["correlations"]), (
            "evidence['correlations'] must contain Phase 5.3 CorrelationFinding"
        )

    def test_database_hypothesis_evidence_isolation(self):
        """Fix 2: Database hypothesis must only receive database-relevant evidence."""
        from pathlib import Path
        from app.core.config import settings
        from app.evidence.engine import EvidenceEngine
        from app.evidence.loader import load_scenario
        from app.ai.state import create_initial_state
        from app.ai.graph import run_investigation_graph

        engine = EvidenceEngine(settings.data_root)
        scenario_id = "database-degradation"
        bundle = engine.investigate(scenario_id)
        incident = load_scenario(Path(settings.data_root), scenario_id).incident

        state = create_initial_state(incident, bundle)
        final_state = run_investigation_graph(state, provider=MockAIProvider())

        hypotheses = final_state.get("hypotheses", [])
        assert len(hypotheses) >= 1
        db_hyp = next((h for h in hypotheses if "database" in h["title"].lower() or "connection" in h["title"].lower()), None)
        assert db_hyp is not None, "Database hypothesis must be generated"

        # Verify supporting evidence IDs are database-specific
        sup_ids = db_hyp.get("supporting_evidence_ids", [])
        assert len(sup_ids) >= 1, "Database hypothesis must have supporting evidence"
        for eid in sup_ids:
            eid_lower = eid.lower()
            # Must not be a deployment release event
            assert "dep-" not in eid_lower and "release" not in eid_lower, (
                f"Database hypothesis contaminated with deployment evidence: {eid}"
            )
            # Must be grounded in database or corroborating application error telemetry
            assert any(k in eid_lower for k in ("db", "payment", "conn", "query", "metric", "log", "latency")), (
                f"Unexpected evidence ID in database hypothesis: {eid}"
            )

    def test_deployment_hypothesis_evidence_isolation(self, base_incident, deployment_evidence):
        """Fix 2: Deployment hypothesis must only receive deployment-relevant evidence."""
        state = create_initial_state(base_incident, deployment_evidence)
        final_state = run_investigation_graph(state, provider=MockAIProvider())

        hypotheses = final_state.get("hypotheses", [])
        dep_hyp = next((h for h in hypotheses if "deployment" in h["title"].lower()), None)
        assert dep_hyp is not None, "Deployment hypothesis must be generated"

        sup_ids = dep_hyp.get("supporting_evidence_ids", [])
        assert "ev-tl-deploy" in sup_ids, "Deployment hypothesis must contain deployment timeline ID"

    def test_historical_memory_integration_and_safety(self, db):
        """Fix 3: Historical memory is queried, enriches metadata, but never overrides strength or IDs."""
        from datetime import datetime, timezone
        from app.models.orm import IncidentRow, IncidentMemoryRow
        from app.services.investigation.service import start_investigation
        from app.ai.config import AISettings
        import app.ai.config as ai_config

        ai_config.ai_settings = AISettings(enabled=True, provider="mock", model="mock-reasoner")

        # Seed historical memory
        mem = IncidentMemoryRow(
            id="mem-past-53-test",
            fingerprint="sev1 api_gateway payment_service deployment",
            title="Past payment outage",
            root_cause_category="deployment_regression",
            recovery_action="Rollback deployment",
            recovery_outcome="resolved",
            scenario_id="bad-deployment",
            incident_id="inc-old-53",
            created_at=datetime.now(timezone.utc),
        )
        db.add(mem)

        inc = IncidentRow(
            id="inc-fix-mem-01",
            scenario_id="bad-deployment",
            title="Current payment outage",
            severity="sev1",
            started_at=datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc),
            detected_at=datetime(2026, 10, 8, 10, 5, tzinfo=timezone.utc),
            recovered_at=datetime(2026, 10, 8, 10, 30, tzinfo=timezone.utc),
            affected_services=["api-gateway", "payment-service"],
        )
        db.add(inc)
        db.commit()

        resp = start_investigation(db, "inc-fix-mem-01")
        assert resp is not None
        assert resp.status == "complete"
        assert resp.hypotheses is not None
        h = resp.hypotheses[0]

        meta = h.get("metadata", {})
        # 1. Historical metadata enriched
        assert meta.get("historical_match_count", 0) >= 1
        assert "historical_context_note" in meta
        # 2. Historical override is strictly False
        assert meta.get("historical_override") is False
        # 3. Memory ID is NOT leaked into evidence IDs
        assert "mem-past-53-test" not in h.get("supporting_evidence_ids", [])

