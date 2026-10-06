"""Tests for AI structured output schemas, strength validation, and evidence reference enforcement."""
import pytest
from pydantic import ValidationError

from app.ai.schemas import (
    AIHypothesis,
    ChallengeResult,
    InvestigationPlan,
    InvestigationPlanStep,
    InvestigatorFinding,
    PostmortemDraft,
    RecoveryRecommendation,
)
from app.ai.validation import (
    AIValidationError,
    extract_valid_evidence_ids,
    validate_evidence_ids,
    validate_hypothesis_references,
)


def test_valid_ai_hypothesis():
    h = AIHypothesis(
        id="hyp-01",
        title="Application regression introduced by recent deployment",
        explanation="Preceding deployment coincided with error rate jump.",
        supporting_evidence_ids=["ev-01", "mf-01"],
        contradicting_evidence_ids=[],
        missing_evidence=[],
        reasoning_summary="Correlated findings support causal link.",
        strength="strongly_supported",
    )
    assert h.id == "hyp-01"
    assert h.strength == "strongly_supported"


def test_unsupported_strength_label_rejected():
    # Arbitrary confidence percentages like "95%" or invalid strings must be rejected
    with pytest.raises(ValidationError):
        AIHypothesis(
            id="hyp-01",
            title="Invalid Strength Hypothesis",
            explanation="Explanation",
            reasoning_summary="Summary",
            strength="95%",  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        AIHypothesis(
            id="hyp-01",
            title="Invalid Strength Hypothesis",
            explanation="Explanation",
            reasoning_summary="Summary",
            strength="highly_probable",  # type: ignore[arg-type]
        )


def test_malformed_ai_hypothesis_rejected():
    # Missing required fields like title or explanation
    with pytest.raises(ValidationError):
        AIHypothesis.model_validate({"id": "hyp-01"})

    # Extra unexpected fields forbidden
    with pytest.raises(ValidationError):
        AIHypothesis.model_validate({
            "id": "hyp-01",
            "title": "Title",
            "explanation": "Exp",
            "reasoning_summary": "Summary",
            "strength": "supported",
            "hallucinated_extra_key": "some value",
        })


def test_investigation_plan_schema():
    plan = InvestigationPlan(
        investigation_id="inv-123",
        steps=[
            InvestigationPlanStep(
                step_id="step-1",
                investigator_type="deployment",
                reason="Evaluate release revision",
                priority=1,
                dependencies=[],
                status="pending",
            )
        ],
        status="planned",
    )
    assert plan.investigation_id == "inv-123"
    assert len(plan.steps) == 1
    assert plan.steps[0].investigator_type == "deployment"


def test_challenge_result_schema():
    cr = ChallengeResult(
        hypothesis_id="hyp-01",
        status="rejected",
        challenge_rationale="Independent logs confirm database deadlock preceded deployment by 3 hours.",
        contradicting_evidence_ids=["ev-log-db-01"],
        independent_evidence_ids=[],
    )
    assert cr.status == "rejected"
    assert cr.contradicting_evidence_ids == ["ev-log-db-01"]


def test_recovery_recommendation_schema():
    rec = RecoveryRecommendation(
        action="Rollback deployment v4.2",
        target="payment-service",
        rationale="Release correlates with observed error rate.",
        expected_impact="Baseline error rate restored.",
        requires_human_approval=True,
        risk_level="low",
        supporting_evidence_ids=["ev-01"],
    )
    assert rec.requires_human_approval is True
    assert rec.risk_level == "low"


def test_postmortem_draft_schema():
    pm = PostmortemDraft(
        title="Postmortem: Checkout Regression",
        summary="Service degradation following deployment.",
        impact_duration_minutes=25.5,
        root_cause_analysis="NullPointerException in payment gateway.",
        causal_sequence=["Deployment", "NPE", "Checkout errors"],
        remediation_summary="Rollback v4.2",
        action_items=["Add integration test"],
        evidence_references=["ev-01"],
    )
    assert pm.impact_duration_minutes == 25.5
    assert len(pm.action_items) == 1


def test_evidence_reference_validation():
    valid_ids = {"ev-01", "ev-02", "mf-01"}

    # Valid references pass without error
    validate_evidence_ids(["ev-01", "mf-01"], valid_ids)

    # Hallucinated / unknown evidence IDs raise AIValidationError
    with pytest.raises(AIValidationError) as exc_info:
        validate_evidence_ids(["ev-01", "ev-hallucinated-999"], valid_ids)
    assert "ev-hallucinated-999" in str(exc_info.value)


def test_hypothesis_reference_validation():
    valid_ids = {"ev-01", "ev-02"}

    valid_h = AIHypothesis(
        id="hyp-01",
        title="Valid Hypothesis",
        explanation="Exp",
        supporting_evidence_ids=["ev-01"],
        contradicting_evidence_ids=["ev-02"],
        missing_evidence=[],
        reasoning_summary="Summary",
        strength="supported",
    )
    validate_hypothesis_references(valid_h, valid_ids)

    invalid_h = AIHypothesis(
        id="hyp-02",
        title="Invalid Hypothesis",
        explanation="Exp",
        supporting_evidence_ids=["ev-fake-id"],
        contradicting_evidence_ids=[],
        missing_evidence=[],
        reasoning_summary="Summary",
        strength="supported",
    )
    with pytest.raises(AIValidationError):
        validate_hypothesis_references(invalid_h, valid_ids)
