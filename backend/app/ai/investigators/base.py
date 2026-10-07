"""Base class and common infrastructure for specialized domain investigators.

Each investigator receives deterministically filtered evidence, performs domain-specific
reasoning (via configured AIProvider or deterministic fallback), and produces a structured,
evidence-validated InvestigatorFinding.
"""
from __future__ import annotations

import abc
import uuid
from typing import Any
from ..providers.base import AIProvider
from ..schemas import EvidenceStrengthLabel, InvestigatorFinding
from ..validation import extract_valid_evidence_ids, validate_finding_references


class BaseInvestigator(abc.ABC):
    """Abstract base for specialized AI domain investigators."""

    investigator_type: str = "generic"
    domain: str = "general"

    @abc.abstractmethod
    def filter_evidence(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministically filter the evidence bundle to this investigator's domain scope."""
        raise NotImplementedError

    @abc.abstractmethod
    def build_deterministic_finding(
        self,
        incident: dict[str, Any],
        filtered_evidence: dict[str, Any],
        all_valid_ids: set[str],
    ) -> InvestigatorFinding:
        """Formulate a deterministic domain finding based on observed filtered telemetry."""
        raise NotImplementedError

    def investigate(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
        provider: AIProvider | None = None,
    ) -> InvestigatorFinding:
        """Execute domain investigation over filtered evidence with reference validation."""
        filtered = self.filter_evidence(incident, evidence)
        all_valid_ids = extract_valid_evidence_ids(evidence)

        finding: InvestigatorFinding | None = None

        # 1. If provider is supplied and not offline mock without canned/custom handler, call it
        if provider is not None and provider.provider_name != "mock":
            prompt = (
                f"Analyze the following {self.domain} telemetry for incident {incident.get('id')}:\n"
                f"{filtered}\n"
                f"Formulate a structured {self.investigator_type} finding with real evidence IDs."
            )
            system_msg = (
                f"You are the TRACEIQ {self.investigator_type.capitalize()} Investigator. "
                "Evaluate observed evidence objectively. Identify supporting evidence, contradicting evidence, "
                "and false leads. Strictly reference evidence IDs present in the input."
            )
            finding = provider.generate_structured(
                InvestigatorFinding,
                prompt=prompt,
                system_message=system_msg,
            )
        elif provider is not None and provider.provider_name == "mock":
            # For mock provider in test mode, check if provider has canned response or should trigger failure
            # If default mock, generate domain-aware mock finding
            finding = self._generate_mock_or_deterministic(incident, filtered, all_valid_ids, provider)
        else:
            finding = self.build_deterministic_finding(incident, filtered, all_valid_ids)

        if finding is None:
            finding = self.build_deterministic_finding(incident, filtered, all_valid_ids)

        # Validate evidence references strictly against the full evidence bundle
        validate_finding_references(finding, all_valid_ids)
        return finding

    def _generate_mock_or_deterministic(
        self,
        incident: dict[str, Any],
        filtered: dict[str, Any],
        all_valid_ids: set[str],
        provider: AIProvider,
    ) -> InvestigatorFinding:
        """Invoke mock provider to test failure modes or return grounded finding."""
        prompt = f"investigator:{self.investigator_type} domain:{self.domain}"
        system_msg = f"Investigator:{self.investigator_type}"

        # If mock provider has failure flags set, calling generate_structured will raise them
        try:
            finding = provider.generate_structured(
                InvestigatorFinding,
                prompt=prompt,
                system_message=system_msg,
            )
            # If mock returned default fixture without matching domain or evidence IDs, ground it with real evidence
            if not finding.supporting_evidence_ids and not finding.evidence_ids:
                return self.build_deterministic_finding(incident, filtered, all_valid_ids)
            return finding
        except Exception:
            raise
