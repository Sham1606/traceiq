"""TRACEIQ AI Foundation & Orchestration Package.

Establishes provider abstraction, structured contracts, LangGraph investigation workflow,
evidence-reference enforcement, ground-truth protection, cross-investigator correlation,
adversarial challenge, historical reasoning, and competing hypothesis generation.
(Phase 5.1 + 5.2 + 5.3)
"""
from __future__ import annotations

from .challenge import challenge_hypothesis
from .config import AISettings, ai_settings
from .correlation import correlate_findings
from .ground_truth import (
    HIDDEN_GROUND_TRUTH_KEYS,
    assert_no_ground_truth,
    contains_ground_truth,
    sanitize_evidence_payload,
)
from .historical import (
    build_fingerprint_from_evidence,
    build_historical_context_note,
    enrich_hypotheses_with_historical_context,
)
from .planner import InvestigationPlanner
from .providers import (
    AIEmptyResponseError,
    AIProvider,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
    MockAIProvider,
    get_ai_provider,
)
from .schemas import (
    AIExecutionError,
    AIHypothesis,
    ChallengeResult,
    CorrelationFinding,
    EvidenceStrengthLabel,
    InvestigationMetadata,
    InvestigationPlan,
    InvestigationPlanStep,
    InvestigatorFinding,
    PostmortemDraft,
    RecoveryRecommendation,
)
from .state import (
    IncidentContext,
    InvestigationState,
    InvestigationStateModel,
    create_initial_state,
    deserialize_state,
    serialize_state,
)
from .investigators import (
    ApplicationInvestigator,
    BaseInvestigator,
    DatabaseInvestigator,
    DependencyInvestigator,
    DeploymentInvestigator,
)
from .validation import (
    extract_valid_evidence_ids,
    validate_evidence_ids,
    validate_finding_references,
    validate_hypothesis_references,
    validate_plan,
)
from .graph import (
    build_investigation_graph,
    run_investigation_graph,
)

__all__ = [
    # Config
    "AISettings",
    "ai_settings",
    # State
    "IncidentContext",
    "InvestigationState",
    "InvestigationStateModel",
    "create_initial_state",
    "serialize_state",
    "deserialize_state",
    # Schemas
    "EvidenceStrengthLabel",
    "InvestigationPlanStep",
    "InvestigationPlan",
    "InvestigatorFinding",
    "AIHypothesis",
    "ChallengeResult",
    "CorrelationFinding",
    "RecoveryRecommendation",
    "PostmortemDraft",
    "AIExecutionError",
    "InvestigationMetadata",
    # Providers
    "AIProvider",
    "MockAIProvider",
    "get_ai_provider",
    "AIProviderError",
    "AITimeoutError",
    "AIRateLimitError",
    "AIEmptyResponseError",
    "AIValidationError",
    # Validation & Ground Truth
    "HIDDEN_GROUND_TRUTH_KEYS",
    "contains_ground_truth",
    "assert_no_ground_truth",
    "sanitize_evidence_payload",
    "extract_valid_evidence_ids",
    "validate_evidence_ids",
    "validate_hypothesis_references",
    "validate_finding_references",
    "validate_plan",
    # Planner & Investigators & Graph
    "InvestigationPlanner",
    "BaseInvestigator",
    "ApplicationInvestigator",
    "DatabaseInvestigator",
    "DeploymentInvestigator",
    "DependencyInvestigator",
    "build_investigation_graph",
    "run_investigation_graph",
    # Phase 5.3: Correlation, Challenge, Historical
    "CorrelationFinding",
    "correlate_findings",
    "challenge_hypothesis",
    "build_fingerprint_from_evidence",
    "build_historical_context_note",
    "enrich_hypotheses_with_historical_context",
]
