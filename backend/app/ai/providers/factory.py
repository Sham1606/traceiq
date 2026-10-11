"""Provider factory for instantiating AI providers based on configuration.
"""
from __future__ import annotations

from ..config import AISettings, ai_settings
from .base import AIProvider, AIProviderError
from .mock import MockAIProvider


def get_ai_provider(config: AISettings | None = None) -> AIProvider:
    """Instantiate exactly the configured, implemented provider or fail clearly."""
    cfg = config or ai_settings

    if cfg.provider == "mock":
        return MockAIProvider(model_name=cfg.model)

    if cfg.provider == "gemini":
        if not cfg.gemini_api_key:
            raise AIProviderError(
                "Gemini AI provider configured but GEMINI_API_KEY is missing from environment."
            )
        if not cfg.model or cfg.model == "mock-reasoner":
            raise AIProviderError(
                "Gemini AI provider requires GEMINI_MODEL (or AI_MODEL) to name the configured model."
            )
        from .gemini import GeminiAIProvider
        return GeminiAIProvider(
            api_key=cfg.gemini_api_key,
            model_name=cfg.model,
            temperature=cfg.temperature,
            timeout_seconds=cfg.timeout_seconds,
            max_retries=cfg.max_retries,
        )

    raise AIProviderError(f"Unsupported AI provider configured: {cfg.provider}")
