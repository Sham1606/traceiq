"""Tests for AI provider abstraction and failure modes."""
import pytest
from pydantic import ValidationError

from app.ai.config import AISettings
from app.ai.providers import (
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
    MockAIProvider,
    GeminiAIProvider,
    get_ai_provider,
)
from app.ai.schemas import AIHypothesis, InvestigationPlan
import json


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


def test_provider_factory_gemini_configuration():
    cfg = AISettings(provider="gemini", model="configured-model", gemini_api_key="test-only-gemini-key")
    provider = get_ai_provider(cfg)
    assert isinstance(provider, GeminiAIProvider)
    assert provider.provider_name == "gemini"
    assert provider.model_name == "configured-model"


def test_provider_factory_requires_gemini_model():
    cfg = AISettings(provider="gemini", gemini_api_key="test-only-gemini-key")
    with pytest.raises(AIProviderError, match=r"GEMINI_MODEL \(or AI_MODEL\)"):
        get_ai_provider(cfg)


def test_environment_gemini_model_overrides_generic_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_MODEL", "mock-reasoner")
    monkeypatch.setenv("GEMINI_MODEL", "configured-gemini-model")
    settings = AISettings.from_env()
    assert settings.model == "configured-gemini-model"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_ai_settings_reject_unsupported_providers(provider):
    with pytest.raises(ValidationError):
        AISettings(provider=provider)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_environment_rejects_unsupported_providers(monkeypatch, provider):
    monkeypatch.setenv("AI_PROVIDER", provider)
    with pytest.raises(ValueError, match="Supported providers are 'mock' and 'gemini'"):
        AISettings.from_env()


def _stub_gemini_client(monkeypatch, status_code, body):
    calls = []

    class StubResponse:
        text = body if isinstance(body, str) else json.dumps(body)
        headers = {}

        def json(self):
            return body if isinstance(body, dict) else json.loads(body)

    class StubClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, json, headers):
            calls.append({"url": url, "headers": headers, "payload": json})
            response = StubResponse()
            response.status_code = status_code
            return response

    monkeypatch.setattr("app.ai.providers.gemini.httpx.Client", StubClient)
    return calls


def _stub_gemini_responses(monkeypatch, responses):
    calls = []

    class StubResponse:
        def __init__(self, status_code, body, headers):
            self.status_code = status_code
            self.headers = headers
            self.text = body if isinstance(body, str) else json.dumps(body)
            self._body = body

        def json(self):
            return self._body if isinstance(self._body, dict) else json.loads(self._body)

    class StubClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, json, headers):
            calls.append({"url": url, "headers": headers, "payload": json})
            status, body, response_headers = responses[min(len(calls) - 1, len(responses) - 1)]
            return StubResponse(status, body, response_headers)

    monkeypatch.setattr("app.ai.providers.gemini.httpx.Client", StubClient)
    return calls


def _valid_plan_response():
    return {
        "candidates": [{"content": {"parts": [{"text": '{"investigation_id":"inv-test","steps":[]}'}]}}]
    }


def _stub_gemini_responses(monkeypatch, responses):
    calls = []

    class StubResponse:
        def __init__(self, status_code, body, headers):
            self.status_code = status_code
            self.headers = headers
            self.text = body if isinstance(body, str) else json.dumps(body)
            self._body = body

        def json(self):
            return self._body if isinstance(self._body, dict) else json.loads(self._body)

    class StubClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, json, headers):
            calls.append({"url": url, "headers": headers, "payload": json})
            status, body, response_headers = responses[min(len(calls) - 1, len(responses) - 1)]
            return StubResponse(status, body, response_headers)

    monkeypatch.setattr("app.ai.providers.gemini.httpx.Client", StubClient)
    return calls


def _valid_plan_response():
    return {
        "candidates": [{"content": {"parts": [{"text": '{"investigation_id":"inv-test","steps":[]}'}]}}]
    }


def test_gemini_retries_429_after_provider_retry_after(monkeypatch):
    responses = [
        (429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}, {"Retry-After": "0.25"}),
        (200, _valid_plan_response(), {}),
    ]
    calls = _stub_gemini_responses(monkeypatch, responses)
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    provider = GeminiAIProvider(
        api_key="test-only-gemini-key",
        model_name="test-gemini-model",
        max_retries=1,
    )

    result = provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert isinstance(result, InvestigationPlan)
    assert len(calls) == 2
    assert delays == [0.25]
    assert provider.runtime_metadata["request_count"] == 2
    assert provider.runtime_metadata["attempt_count"] == 2
    assert provider.runtime_metadata["retry_count"] == 1
    assert provider.runtime_metadata["retry_after_seconds"] == 0.25
    assert provider.runtime_metadata["status"] == "success"


def test_gemini_retries_transient_server_error_with_bounded_backoff(monkeypatch):
    responses = [
        (503, {"error": {"status": "UNAVAILABLE"}}, {}),
        (200, _valid_plan_response(), {}),
    ]
    calls = _stub_gemini_responses(monkeypatch, responses)
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    monkeypatch.setattr("app.ai.providers.gemini.random.uniform", lambda low, high: 0)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 2
    assert delays == [0.5]


def test_gemini_does_not_retry_daily_quota_or_authentication_errors(monkeypatch):
    cases = [
        (429, {"error": {"status": "quota_exceeded"}}, AIRateLimitError, "quota_exhausted"),
        (401, {"error": {"status": "AUTHENTICATION"}}, AIProviderError, "authentication"),
    ]
    for status, body, error_type, expected_category in cases:
        calls = _stub_gemini_responses(monkeypatch, [(status, body, {"Retry-After": "0.1"})])
        with pytest.raises(error_type) as exc_info:
            GeminiAIProvider("test-only-gemini-key", "test-gemini-model").generate_structured(
                InvestigationPlan,
                prompt="Create plan",
            )
        assert len(calls) == 1
        assert exc_info.value.retryable is False
        assert exc_info.value.category == expected_category
        assert exc_info.value.status_code == status


def test_gemini_does_not_wait_beyond_retry_after_bound(monkeypatch):
    calls = _stub_gemini_responses(
        monkeypatch,
        [(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, {"Retry-After": "60"})],
    )
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 1
    assert delays == []
    assert exc_info.value.retry_after_seconds == 60


def test_gemini_uses_header_auth_and_never_puts_key_in_url(monkeypatch):
    api_key = "test-only-gemini-key-not-a-credential"
    response = {
        "candidates": [{"content": {"parts": [{"text": '{"investigation_id":"inv-test","steps":[]}'}]}}]
    }
    calls = _stub_gemini_client(monkeypatch, 200, response)
    provider = GeminiAIProvider(api_key=api_key, model_name="test-gemini-model")

    result = provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert calls[0]["url"].startswith("https://generativelanguage.googleapis.com/")
    assert "?" not in calls[0]["url"]
    assert api_key not in calls[0]["url"]
    assert calls[0]["headers"]["x-goog-api-key"] == api_key
    assert "/models/test-gemini-model:generateContent" in calls[0]["url"]
    assert calls[0]["payload"]["generationConfig"]["responseMimeType"] == "application/json"
    assert api_key not in json.dumps(calls[0]["payload"])
    assert api_key not in json.dumps(result.model_dump(mode="json"))
    assert provider.successful_calls == 1
    runtime = provider.runtime_metadata
    assert runtime["status"] == "success"
    assert runtime["structured_output_valid"] is True
    assert isinstance(runtime["latency_ms"], int)
    assert runtime["request_started_at"]
    assert runtime["request_completed_at"]


def test_gemini_redacts_key_from_provider_errors(monkeypatch, caplog):
    api_key = "test-only-gemini-key-not-a-credential"
    calls = _stub_gemini_client(monkeypatch, 500, f"upstream echoed {api_key}")
    provider = GeminiAIProvider(api_key=api_key, model_name="test-gemini-model")

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert api_key not in calls[0]["url"]
    assert api_key not in str(exc_info.value)
    assert api_key not in caplog.text
    assert provider.runtime_metadata["status"] == "unavailable"


def test_gemini_rejects_model_output_that_echoes_key(monkeypatch):
    api_key = "test-only-gemini-key-not-a-credential"
    response = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({"investigation_id": api_key, "steps": []})}]}}]
    }
    calls = _stub_gemini_client(monkeypatch, 200, response)
    provider = GeminiAIProvider(api_key=api_key, model_name="test-gemini-model")

    with pytest.raises(AIValidationError) as exc_info:
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert api_key not in calls[0]["url"]
    assert api_key not in str(exc_info.value)
    assert exc_info.value.category == "credential_echo"
    assert exc_info.value.retryable is False


def test_gemini_retries_malformed_json_once_then_rejects(monkeypatch):
    calls = _stub_gemini_client(monkeypatch, 200, "not-json")
    provider = GeminiAIProvider(api_key="test-only-gemini-key", model_name="test-gemini-model")

    with pytest.raises(AIValidationError):
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 2
    assert provider.runtime_metadata["status"] == "invalid"
    assert provider.runtime_metadata["structured_output_valid"] is False


def test_gemini_rate_limit_honors_retry_after_once(monkeypatch):
    calls = _stub_gemini_responses(monkeypatch, [
        (429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}, {"Retry-After": "0.25"}),
        (200, _valid_plan_response(), {}),
    ])
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    result = provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert isinstance(result, InvestigationPlan)
    assert len(calls) == 2
    assert delays == [0.25]
    assert provider.runtime_metadata["request_count"] == 2
    assert provider.runtime_metadata["attempt_count"] == 2


def test_gemini_transient_server_error_uses_bounded_backoff(monkeypatch):
    calls = _stub_gemini_responses(monkeypatch, [
        (503, {"error": {"status": "UNAVAILABLE"}}, {}),
        (200, _valid_plan_response(), {}),
    ])
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    monkeypatch.setattr("app.ai.providers.gemini.random.uniform", lambda low, high: 0.0)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 2
    assert delays == [0.5]


@pytest.mark.parametrize(
    ("status", "body", "error_type", "category"),
    [
        (429, {"error": {"status": "quota_exceeded"}}, AIRateLimitError, "quota_exhausted"),
        (401, {"error": {"status": "AUTHENTICATION"}}, AIProviderError, "authentication"),
    ],
)
def test_gemini_does_not_retry_quota_or_authentication(monkeypatch, status, body, error_type, category):
    calls = _stub_gemini_responses(monkeypatch, [(status, body, {"Retry-After": "0.1"})])
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    with pytest.raises(error_type) as exc_info:
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 1
    assert delays == []
    assert exc_info.value.category == category
    assert exc_info.value.retryable is False
    assert exc_info.value.status_code == status


def test_gemini_does_not_wait_beyond_retry_after_cap(monkeypatch):
    calls = _stub_gemini_responses(monkeypatch, [
        (429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, {"Retry-After": "60"}),
    ])
    delays = []
    monkeypatch.setattr("app.ai.providers.gemini.time.sleep", delays.append)
    provider = GeminiAIProvider("test-only-gemini-key", "test-gemini-model", max_retries=1)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_structured(InvestigationPlan, prompt="Create plan")

    assert len(calls) == 1
    assert delays == []
    assert exc_info.value.retry_after_seconds == 60
