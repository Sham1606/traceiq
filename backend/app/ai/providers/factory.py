"""Provider factory for instantiating AI providers based on configuration.
"""
from __future__ import annotations

from ..config import AISettings, ai_settings
from .base import AIProvider, AIProviderError
from .mock import MockAIProvider


def get_ai_provider(config: AISettings | None = None) -> AIProvider:
    """Factory function to instantiate the configured AI provider.

    Defaults to MockAIProvider if mock is specified or credentials are absent in test mode.
    """
    cfg = config or ai_settings

    if cfg.provider == "mock":
        return MockAIProvider(model_name=cfg.model)

    if cfg.provider == "gemini":
        if not cfg.gemini_api_key:
            raise AIProviderError(
                "Gemini AI provider configured but GEMINI_API_KEY is missing from environment."
            )
        # Gemini provider instantiation (can be loaded dynamically)
        # For Phase 5.1 foundation, if library is not present or credentials missing, raise clean error
        try:
            from .gemini import GeminiAIProvider
            return GeminiAIProvider(
                api_key=cfg.gemini_api_key,
                model_name=cfg.model,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
        except ImportError:
            raise AIProviderError(
                "Gemini provider dependencies not installed. Ensure langchain-google-genai is available."
            )

    if cfg.provider == "openai":
        if not cfg.openai_api_key:
            raise AIProviderError(
                "OpenAI provider configured but OPENAI_API_KEY is missing from environment."
            )
        try:
            from .openai import OpenAIAIProvider
            return OpenAIAIProvider(
                api_key=cfg.openai_api_key,
                model_name=cfg.model,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
        except ImportError:
            raise AIProviderError(
                "OpenAI provider dependencies not installed. Ensure langchain-openai is available."
            )

    raise AIProviderError(f"Unsupported AI provider configured: {cfg.provider}")
