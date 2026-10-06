"""Tests for AI provider abstraction and failure modes."""
import pytest
from pydantic import ValidationError

from app.ai.config import AISettings
from app.ai.providers import (
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    MockAIProvider,
    get_ai_provider,
)
from app.ai.schemas import AIHypothesis, InvestigationPlan


def test_mock_provider_successful_structured_generation():
    provider = MockAIProvider()
    plan = provider.generate_structured(InvestigationPlan, prompt="Create plan for incident")

    assert isinstance(plan, InvestigationPlan)
    assert len(plan.steps) >= 1
    assert len(provider.call_history) == 1
    assert provider.call_history[0]["schema"] == "InvestigationPlan"


def test_mock_provider_timeout_failure():
    provider = MockAIProvider(should_timeout=True)

    with pytest.raises(AITimeoutError) as exc_info:
        provider.generate_structured(AIHypothesis, prompt="Generate hypothesis")
    assert "timed out" in str(exc_info.value).lower()


def test_mock_provider_rate_limit_failure():
    provider = MockAIProvider(should_rate_limit=True)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_structured(AIHypothesis, prompt="Generate hypothesis")
    assert "rate limit" in str(exc_info.value).lower()


def test_mock_provider_error_failure():
    provider = MockAIProvider(should_error=True)

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_structured(AIHypothesis, prompt="Generate hypothesis")
    assert "server error" in str(exc_info.value).lower()


def test_mock_provider_empty_response():
    provider = MockAIProvider(should_empty=True)

    with pytest.raises(AIEmptyResponseError) as exc_info:
        provider.generate_structured(AIHypothesis, prompt="Generate hypothesis")
    assert "empty response" in str(exc_info.value).lower()


def test_mock_provider_malformed_output():
    provider = MockAIProvider(malformed_output=True)

    with pytest.raises(ValidationError):
        provider.generate_structured(AIHypothesis, prompt="Generate hypothesis")


def test_provider_factory_mock():
    cfg = AISettings(provider="mock", model="custom-mock")
    provider = get_ai_provider(cfg)
    assert provider.provider_name == "mock"
    assert provider.model_name == "custom-mock"


def test_provider_factory_missing_gemini_key():
    cfg = AISettings(provider="gemini", gemini_api_key=None)
    with pytest.raises(AIProviderError) as exc_info:
        get_ai_provider(cfg)
    assert "GEMINI_API_KEY is missing" in str(exc_info.value)


def test_provider_factory_missing_openai_key():
    cfg = AISettings(provider="openai", openai_api_key=None)
    with pytest.raises(AIProviderError) as exc_info:
        get_ai_provider(cfg)
    assert "OPENAI_API_KEY is missing" in str(exc_info.value)
