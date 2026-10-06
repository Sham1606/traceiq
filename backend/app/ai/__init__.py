"""TRACEIQ AI Foundation & Orchestration Package.

Establishes provider abstraction, structured contracts, LangGraph investigation workflow,
evidence-reference enforcement, and ground-truth protection.
"""
from __future__ import annotations

from .config import AISettings, ai_settings
from .ground_truth import (
    HIDDEN_GROUND_TRUTH_KEYS,
    assert_no_ground_truth,
    contains_ground_truth,
    sanitize_evidence_payload,
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
from .validation import (
    extract_valid_evidence_ids,
    validate_evidence_ids,
    validate_finding_references,
    validate_hypothesis_references,
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
    # Planner & Graph
    "InvestigationPlanner",
    "build_investigation_graph",
    "run_investigation_graph",
]
