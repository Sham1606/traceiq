"""AI Provider abstraction and exception hierarchy.

Permits transparent substitution between the mock test provider and Gemini
without tight coupling.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

from ..validation import AIValidationError

T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Base exception for all AI provider communication or execution failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        provider_code: str | None = None,
        category: str | None = None,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
        attempt_count: int = 1,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider_code = provider_code
        self.category = category
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.attempt_count = attempt_count


class AITimeoutError(AIProviderError):
    """Raised when an AI provider call exceeds configured timeout."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when an AI provider returns HTTP 429 or quota exhaustion."""
    pass


class AIEmptyResponseError(AIProviderError):
    """Raised when an AI provider returns an empty payload."""
    pass


class AIProvider(ABC):
    """Abstract interface for structured AI model interactions."""

    @abstractmethod
    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_message: str | None = None,
    ) -> T:
        """Generate and validate a structured response adhering to the given Pydantic schema."""
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the identifier of this AI provider."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier currently configured."""
        raise NotImplementedError
