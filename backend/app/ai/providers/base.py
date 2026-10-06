"""AI Provider abstraction and exception hierarchy.

Permits transparent substitution between mock test providers, Gemini, OpenAI,
or local models without tight coupling.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

from ..validation import AIValidationError

T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Base exception for all AI provider communication or execution failures."""
    pass


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
