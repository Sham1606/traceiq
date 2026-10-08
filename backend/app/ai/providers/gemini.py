"""Gemini AI Provider for live LLM reasoning over normalized incident evidence.

Uses Google Generative Language REST API with structured JSON output mode.
Adheres strictly to the AIProvider interface and error hierarchy.
Credentials are read strictly from environment variable GEMINI_API_KEY.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TypeVar
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
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.1,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise AIProviderError("Gemini API key is required but was not provided.")
        self._api_key = api_key
        # Normalize model name for API (e.g. models/gemini-1.5-flash -> gemini-1.5-flash)
        clean_model = model_name.replace("models/", "")
        self._model_name = clean_model if clean_model != "mock-reasoner" else "gemini-1.5-flash"
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_message: str | None = None,
    ) -> T:
        """Generate structured response adhering to Pydantic schema using Gemini."""
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

        url = f"{GEMINI_API_BASE}/models/{self._model_name}:generateContent?key={self._api_key}"

        # Try request with 1 immediate retry on transient network/validation error
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    resp = client.post(url, json=payload)

                if resp.status_code == 429:
                    raise AIRateLimitError("Gemini API quota exceeded or rate limit (HTTP 429).")
                if resp.status_code == 408:
                    raise AITimeoutError("Gemini API request timed out (HTTP 408).")
                if resp.status_code >= 500:
                    raise AIProviderError(f"Gemini API server error (HTTP {resp.status_code}): {resp.text[:300]}")
                if resp.status_code != 200:
                    raise AIProviderError(f"Gemini API call failed (HTTP {resp.status_code}): {resp.text[:300]}")

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise AIEmptyResponseError("Gemini returned zero candidates.")

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise AIEmptyResponseError("Gemini candidate content has no text parts.")

                raw_text = parts[0].get("text", "")
                cleaned_text = _clean_json_text(raw_text)
                if not cleaned_text:
                    raise AIEmptyResponseError("Gemini returned empty text payload.")

                parsed_dict = json.loads(cleaned_text)
                return schema.model_validate(parsed_dict)

            except (httpx.TimeoutException, TimeoutError) as te:
                last_error = AITimeoutError(f"Gemini request timed out after {self._timeout_seconds}s: {te}")
                break  # Don't retry timeouts
            except httpx.RequestError as re:
                last_error = AIProviderError(f"Gemini network connection error: {re}")
            except json.JSONDecodeError as jde:
                last_error = AIValidationError(f"Gemini returned invalid JSON: {jde}")
            except ValidationError as ve:
                last_error = AIValidationError(f"Gemini output failed schema validation: {ve}")
            except (AIRateLimitError, AITimeoutError):
                raise
            except Exception as e:
                last_error = AIProviderError(f"Gemini execution error: {e}")

        if last_error:
            logger.warning("Gemini provider structured generation failed: %s", last_error)
            raise last_error

        raise AIProviderError("Gemini call failed with unknown error.")
