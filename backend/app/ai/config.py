"""AI configuration loaded from environment variables with safe defaults.

No API keys are hardcoded. Secrets are never logged or exposed in __repr__.
"""
from __future__ import annotations

import os
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AISettings(BaseModel):
    """Typed AI settings loaded from environment variables."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False)
    provider: Literal["mock", "gemini"] = Field(default="mock")
    model: str = Field(default="mock-reasoner")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    max_retries: int = Field(default=1, ge=0, le=1)

    # API keys (masked in representation)
    gemini_api_key: str | None = Field(default=None)

    @classmethod
    def from_env(cls) -> AISettings:
        """Instantiate settings from environment variables."""
        enabled_raw = os.environ.get("AI_ENABLED", "0").lower()
        enabled = enabled_raw in {"1", "true", "yes", "on"}

        provider_raw = os.environ.get("AI_PROVIDER", "mock").lower()
        if provider_raw not in {"mock", "gemini"}:
            raise ValueError("Unsupported AI_PROVIDER. Supported providers are 'mock' and 'gemini'.")

        model = os.environ.get("AI_MODEL", "mock-reasoner")
        if provider_raw == "gemini":
            model = os.environ.get("GEMINI_MODEL") or model

        try:
            temperature = float(os.environ.get("AI_TEMPERATURE", "0.0"))
        except ValueError:
            temperature = 0.0

        try:
            timeout_seconds = float(os.environ.get("AI_TIMEOUT_SECONDS", "30.0"))
        except ValueError:
            timeout_seconds = 30.0

        try:
            max_retries = int(os.environ.get("AI_MAX_RETRIES", "1"))
        except ValueError:
            max_retries = 1

        return cls(
            enabled=enabled,
            provider=provider_raw,  # type: ignore[arg-type]
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        )

    def is_provider_available(self) -> bool:
        """Check if required credentials for current provider are configured."""
        if self.provider == "mock":
            return True
        if self.provider == "gemini":
            return bool(self.gemini_api_key and self.model and self.model != "mock-reasoner")
        return False

    def __repr__(self) -> str:
        """Mask credentials to prevent accidental logging leaks."""
        return (
            f"AISettings(enabled={self.enabled}, provider='{self.provider}', "
            f"model='{self.model}', temperature={self.temperature}, "
            f"timeout_seconds={self.timeout_seconds}, max_retries={self.max_retries}, "
            f"has_key={self.is_provider_available()})"
        )


ai_settings = AISettings.from_env()
