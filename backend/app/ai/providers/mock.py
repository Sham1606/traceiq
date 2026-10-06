"""Mock AI provider for deterministic testing, CI validation, and failure simulation.

Does not make any live network requests. Supports programmable failure modes:
timeouts, rate limits, malformed responses, and custom schema fixtures.
"""
from __future__ import annotations

from typing import Any, TypeVar
from pydantic import BaseModel

from .base import (
    AIEmptyResponseError,
    AIProvider,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from ..schemas import (
    AIHypothesis,
    ChallengeResult,
    InvestigationPlan,
    InvestigationPlanStep,
    InvestigatorFinding,
    PostmortemDraft,
    RecoveryRecommendation,
)

T = TypeVar("T", bound=BaseModel)


class MockAIProvider(AIProvider):
    """Programmable mock provider for deterministic AI layer testing."""

    def __init__(
        self,
        model_name: str = "mock-reasoner",
        should_timeout: bool = False,
        should_rate_limit: bool = False,
        should_error: bool = False,
        should_empty: bool = False,
        malformed_output: bool = False,
        canned_responses: dict[type, Any] | None = None,
    ) -> None:
        self._model_name = model_name
        self.should_timeout = should_timeout
        self.should_rate_limit = should_rate_limit
        self.should_error = should_error
        self.should_empty = should_empty
        self.malformed_output = malformed_output
        self.canned_responses = canned_responses or {}
        self.call_history: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_message: str | None = None,
    ) -> T:
        """Return a typed response or trigger configured failure simulation."""
        self.call_history.append({
            "schema": schema.__name__,
            "prompt": prompt,
            "system_message": system_message,
        })

        if self.should_timeout:
            raise AITimeoutError("Mock provider call timed out after configured duration.")

        if self.should_rate_limit:
            raise AIRateLimitError("Mock provider rate limit exceeded (HTTP 429).")

        if self.should_error:
            raise AIProviderError("Mock provider internal server error (HTTP 500).")

        if self.should_empty:
            raise AIEmptyResponseError("Mock provider returned empty response payload.")

        if self.malformed_output:
            # Attempt to construct an invalid instance that violates schema
            # by calling model_validate with empty/invalid dict
            return schema.model_validate({"invalid_field_123": True})

        if schema in self.canned_responses:
            val = self.canned_responses[schema]
            if isinstance(val, schema):
                return val
            if isinstance(val, dict):
                return schema.model_validate(val)
            raise ValueError(f"Invalid canned response type for {schema}: {type(val)}")

        # Provide sensible default deterministic fixture per schema type
        return self._generate_default_fixture(schema)

    def _generate_default_fixture(self, schema: type[T]) -> T:
        if schema == AIHypothesis:
            return schema.model_validate({
                "id": "hyp-ai-01",
                "title": "Application regression introduced by recent deployment",
                "explanation": "Deployment directly precedes observed metric shift.",
                "supporting_evidence_ids": [],
                "contradicting_evidence_ids": [],
                "missing_evidence": [],
                "reasoning_summary": "Correlation findings establish causal ordering.",
                "strength": "strongly_supported",
            })

        if schema == InvestigationPlan:
            return schema.model_validate({
                "investigation_id": "inv-mock-01",
                "status": "planned",
                "steps": [
                    {
                        "step_id": "step-1",
                        "investigator_type": "deployment",
                        "reason": "Production deployment logged in window",
                        "priority": 1,
                        "dependencies": [],
                        "status": "pending",
                    },
                    {
                        "step_id": "step-2",
                        "investigator_type": "application",
                        "reason": "Anomalous error rate detected in web services",
                        "priority": 2,
                        "dependencies": ["step-1"],
                        "status": "pending",
                    },
                ],
            })

        if schema == InvestigatorFinding:
            return schema.model_validate({
                "finding_id": "find-01",
                "investigator_type": "application",
                "domain": "telemetry",
                "summary": "Elevated error rate across api-gateway and payment-service",
                "evidence_ids": [],
                "anomalies_detected": ["error_rate"],
                "confidence_label": "strongly_supported",
                "metadata": {"source": "mock"},
            })

        if schema == ChallengeResult:
            return schema.model_validate({
                "hypothesis_id": "hyp-ai-01",
                "status": "supported",
                "challenge_rationale": "No contradicting timeline events or logs identified.",
                "contradicting_evidence_ids": [],
                "independent_evidence_ids": [],
                "challenger_agent": "ChallengeAgent",
            })

        if schema == RecoveryRecommendation:
            return schema.model_validate({
                "action": "Rollback deployment release v4.2",
                "target": "payment-service",
                "rationale": "Deployment regression is strongly supported by telemetry deltas.",
                "expected_impact": "Error rate restoration to baseline <0.01%",
                "requires_human_approval": True,
                "risk_level": "medium",
                "supporting_evidence_ids": [],
            })

        if schema == PostmortemDraft:
            return schema.model_validate({
                "title": "Incident Postmortem: Payment API Regression",
                "summary": "Service degradation following production deployment release.",
                "impact_duration_minutes": 22.0,
                "root_cause_analysis": "NullPointerException in PaymentHandler introduced in v4.2 release.",
                "causal_sequence": ["Deployment v4.2", "Error rate jump", "Checkout failures"],
                "remediation_summary": "Rolled back to v4.1.",
                "action_items": ["Add automated canary tests for payment endpoints"],
                "evidence_references": [],
            })

        # Generic fallback
        return schema.model_validate({})
