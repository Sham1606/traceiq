"""Gemini AI Provider for live LLM reasoning over normalized incident evidence.

Uses Google Generative Language REST API with structured JSON output mode.
Adheres strictly to the AIProvider interface and error hierarchy.
Credentials are read strictly from environment variable GEMINI_API_KEY.
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TypeVar
from urllib.parse import quote, quote_plus
import httpx
from pydantic import BaseModel, ValidationError

from .base import (
    AIEmptyResponseError,
    AIProvider,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from ..validation import AIValidationError

logger = logging.getLogger("traceiq.ai.gemini")

T = TypeVar("T", bound=BaseModel)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MAX_PROVIDER_RETRY_AFTER_SECONDS = 10.0
BASE_RETRY_DELAY_SECONDS = 0.5
MAX_RETRY_DELAY_SECONDS = 5.0


def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code block fences if present in model output."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


class GeminiAIProvider(AIProvider):
    """Runtime AI provider backed by Google's Gemini API."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        temperature: float = 0.1,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        if not api_key:
            raise AIProviderError("Gemini API key is required but was not provided.")
        if not model_name or model_name == "mock-reasoner":
            raise AIProviderError("A configured Gemini model name is required.")
        self._api_key = api_key
        self._model_name = model_name.removeprefix("models/")
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, min(max_retries, 2))
        self._successful_calls = 0
        self._failed_calls = 0
        self._request_count = 0
        self._last_attempt_count = 0
        self._retry_count = 0
        self._request_started_at: str | None = None
        self._request_completed_at: str | None = None
        self._total_latency_ms = 0
        self._request_latency_ms: int | None = None
        self._request_status = "not_started"
        self._http_status: int | None = None
        self._provider_code: str | None = None
        self._failure_category: str | None = None
        self._retry_after_seconds: float | None = None
        self._evidence_ids_referenced: set[str] = set()
        self._validated_result: T | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def successful_calls(self) -> int:
        return self._successful_calls

    @property
    def runtime_metadata(self) -> dict[str, object]:
        return {
            "request_started_at": self._request_started_at,
            "request_completed_at": self._request_completed_at,
            "latency_ms": self._total_latency_ms,
            "last_request_latency_ms": self._request_latency_ms,
            "request_count": self._request_count,
            "attempt_count": self._last_attempt_count,
            "retry_count": self._retry_count,
            "successful_calls": self._successful_calls,
            "failed_calls": self._failed_calls,
            "status": "success" if self._successful_calls else self._request_status,
            "structured_output_valid": self._successful_calls > 0,
            "evidence_ids_referenced": len(self._evidence_ids_referenced),
            "http_status": self._http_status,
            "provider_code": self._provider_code,
            "failure_category": self._failure_category,
            "retry_after_seconds": self._retry_after_seconds,
        }

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value.strip()))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    @staticmethod
    def _safe_provider_code(response: httpx.Response) -> str | None:
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError):
            return None
        error = body.get("error") if isinstance(body, dict) else None
        if not isinstance(error, dict):
            return None
        raw_code = error.get("status") or error.get("code")
        if isinstance(raw_code, int):
            return f"HTTP_{raw_code}"
        if isinstance(raw_code, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", raw_code):
            return raw_code
        return None

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        base = min(BASE_RETRY_DELAY_SECONDS * (2 ** max(0, attempt - 1)), MAX_RETRY_DELAY_SECONDS)
        return base + random.uniform(0.0, min(0.25, MAX_RETRY_DELAY_SECONDS - base))

    def _store_failure_metadata(self, error: AIProviderError) -> None:
        self._http_status = getattr(error, "status_code", None)
        self._provider_code = getattr(error, "provider_code", None)
        self._failure_category = getattr(error, "category", None)
        self._retry_after_seconds = getattr(error, "retry_after_seconds", None)

    def _wait_before_retry(self, error: AIProviderError, attempt: int) -> bool:
        if not getattr(error, "retryable", False) or attempt > self._max_retries:
            return False
        retry_after = getattr(error, "retry_after_seconds", None)
        if retry_after is not None:
            if retry_after > MAX_PROVIDER_RETRY_AFTER_SECONDS:
                return False
            delay = retry_after
        else:
            delay = self._backoff_seconds(attempt)
        time.sleep(delay)
        return True

    def _redact_key(self, text: str) -> str:
        for candidate in (self._api_key, quote(self._api_key, safe=""), quote_plus(self._api_key)):
            if candidate:
                text = text.replace(candidate, "[REDACTED]")
        return text

    def _contains_key(self, text: str) -> bool:
        candidates = (self._api_key, quote(self._api_key, safe=""), quote_plus(self._api_key))
        return any(candidate and candidate in text for candidate in candidates)

    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_message: str | None = None,
    ) -> T:
        """Generate structured response adhering to Pydantic schema using Gemini."""
        started_at = datetime.now(timezone.utc)
        started_clock = time.perf_counter()
        if self._request_started_at is None:
            self._request_started_at = started_at.isoformat()
        self._request_status = "running"
        self._last_attempt_count = 0
        self._http_status = None
        self._provider_code = None
        self._failure_category = None
        self._retry_after_seconds = None
        self._validated_result = None
        try:
            result = self._generate_structured(schema, prompt, system_message)
            self._request_status = "success"
            self._collect_evidence_references(result.model_dump(mode="json"))
            return result
        except Exception as exc:
            self._failed_calls += 1
            self._request_status = "invalid" if isinstance(exc, AIValidationError) else "unavailable"
            raise
        finally:
            self._request_completed_at = datetime.now(timezone.utc).isoformat()
            self._request_latency_ms = round((time.perf_counter() - started_clock) * 1000)
            self._total_latency_ms += self._request_latency_ms

    def _collect_evidence_references(self, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key.endswith("evidence_ids"):
                    if isinstance(nested, list):
                        self._evidence_ids_referenced.update(str(item) for item in nested)
                else:
                    self._collect_evidence_references(nested)
        elif isinstance(value, list):
            for item in value:
                self._collect_evidence_references(item)

    def _generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_message: str | None = None,
    ) -> T:
        """Send and validate one structured Gemini response."""
        schema_json_schema = json.dumps(schema.model_json_schema())

        system_instruction_text = (
            f"{system_message or 'You are TRACEIQ Root Cause Investigator.'}\n\n"
            f"You MUST output valid JSON conforming exactly to this JSON Schema:\n{schema_json_schema}\n"
            "Rules:\n"
            "1. Output ONLY a single JSON object. No explanations or comments outside the JSON.\n"
            "2. Never hallucinate evidence IDs. Only reference evidence IDs present in the prompt."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction_text}],
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": self._temperature,
            },
        }

        url = f"{GEMINI_API_BASE}/models/{self._model_name}:generateContent"

        for attempt in range(1, self._max_retries + 2):
            self._last_attempt_count = attempt
            self._request_count += 1
            error: AIProviderError | None = None
            response: httpx.Response | None = None

            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers={"x-goog-api-key": self._api_key},
                    )
            except (httpx.TimeoutException, TimeoutError):
                error = AITimeoutError(
                    "Gemini request exceeded the configured timeout.",
                    category="timeout",
                    retryable=True,
                    attempt_count=attempt,
                )
            except httpx.RequestError:
                error = AIProviderError(
                    "Gemini transport request failed.",
                    category="network",
                    retryable=True,
                    attempt_count=attempt,
                )

            if response is not None:
                self._http_status = response.status_code
                self._provider_code = self._safe_provider_code(response)
                retry_after = self._parse_retry_after(response.headers.get("Retry-After"))

                if response.status_code != 200:
                    code = (self._provider_code or "").lower()
                    if response.status_code == 429:
                        daily_quota = code in {"quota_exceeded", "daily_quota_exceeded"}
                        error_type = AIRateLimitError
                        category = "quota_exhausted" if daily_quota else "rate_limit"
                        retryable = not daily_quota
                        message = "Gemini quota is exhausted." if daily_quota else "Gemini rate limit was reached."
                    elif response.status_code == 408:
                        error_type = AITimeoutError
                        category = "timeout"
                        retryable = True
                        message = "Gemini request timed out."
                    elif response.status_code >= 500:
                        error_type = AIProviderError
                        category = "provider_server_error"
                        retryable = True
                        message = "Gemini returned a transient server error."
                    else:
                        error_type = AIProviderError
                        category = {
                            400: "invalid_request",
                            401: "authentication",
                            403: "permission_denied",
                            404: "model_not_found" if "model" in code else "not_found",
                        }.get(response.status_code, "provider_request_error")
                        retryable = False
                        message = "Gemini rejected the request."
                    error = error_type(
                        message,
                        status_code=response.status_code,
                        provider_code=self._provider_code,
                        category=category,
                        retryable=retryable,
                        retry_after_seconds=retry_after,
                        attempt_count=attempt,
                    )
                elif error is None:
                    error = self._validate_response(schema, response, attempt)

            if error is None:
                if response is None:
                    error = AIProviderError(
                        "Gemini request failed without a classified error.",
                        category="provider_error",
                        attempt_count=attempt,
                    )
                else:
                    self._request_status = "success"
                    self._http_status = response.status_code
                    self._provider_code = None
                    self._failure_category = None
                    self._successful_calls += 1
                    result = self._validated_result
                    self._collect_evidence_references(result.model_dump(mode="json"))
                    return result

            error.attempt_count = attempt
            self._store_failure_metadata(error)
            if self._wait_before_retry(error, attempt):
                self._retry_count += 1
                logger.info(
                    "Gemini retry scheduled: status=%s code=%s category=%s attempt=%s retry_after=%s",
                    getattr(error, "status_code", None),
                    getattr(error, "provider_code", None),
                    getattr(error, "category", None),
                    attempt,
                    getattr(error, "retry_after_seconds", None),
                )
                continue

            logger.warning(
                "Gemini request failed: status=%s code=%s category=%s retryable=%s attempts=%s",
                getattr(error, "status_code", None),
                getattr(error, "provider_code", None),
                getattr(error, "category", None),
                getattr(error, "retryable", False),
                attempt,
            )
            raise error

        raise AIProviderError("Gemini request ended without a response.", category="provider_error")

    def _validate_response(
        self,
        schema: type[T],
        response: httpx.Response,
        attempt: int,
    ) -> AIProviderError | AIValidationError | None:
        try:
            data = response.json()
            candidates = data.get("candidates", [])
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            raw_text = parts[0].get("text", "") if parts else ""
            cleaned_text = _clean_json_text(raw_text)
            if not cleaned_text:
                return AIEmptyResponseError(
                    "Gemini returned no structured text.",
                    category="empty_response",
                    retryable=True,
                    attempt_count=attempt,
                    status_code=response.status_code,
                )
            if self._contains_key(cleaned_text):
                return AIValidationError(
                    "Gemini output contained credential material and was rejected.",
                    category="credential_echo",
                    retryable=False,
                    attempt_count=attempt,
                    status_code=response.status_code,
                )
            parsed = json.loads(cleaned_text)
            result = schema.model_validate(parsed)
            if self._contains_key(json.dumps(result.model_dump(mode="json"))):
                return AIValidationError(
                    "Gemini output contained credential material and was rejected.",
                    category="credential_echo",
                    retryable=False,
                    attempt_count=attempt,
                    status_code=response.status_code,
                )
            self._validated_result = result
            return None
        except json.JSONDecodeError:
            return AIValidationError(
                "Gemini output was not valid JSON.",
                category="structured_output_validation",
                retryable=True,
                attempt_count=attempt,
                status_code=response.status_code,
            )
        except ValidationError as exc:
            field_paths = sorted({
                ".".join(str(part) for part in item.get("loc", ()))
                for item in exc.errors(include_input=False, include_context=False, include_url=False)
            })[:5]
            return AIValidationError(
                "Gemini output did not match the required structured schema.",
                category="structured_output_validation",
                retryable=True,
                attempt_count=attempt,
                status_code=response.status_code,
                schema_fields=field_paths,
            )
