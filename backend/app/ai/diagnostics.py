"""Safe, bounded diagnostics for provider and investigation-stage failures."""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError


def safe_error_diagnostic(error: Exception) -> dict[str, Any]:
    """Describe an error without including arbitrary exception text or values."""
    error_class = type(error).__name__
    lowered = str(error).lower()

    if error_class == "AITimeoutError":
        category = "timeout"
        explanation = "The provider request exceeded its configured timeout."
        retryable = True
    elif error_class == "AIRateLimitError":
        category = "rate_limit"
        explanation = "The provider rejected the request due to rate limiting or quota."
        retryable = True
    elif error_class == "AIEmptyResponseError":
        category = "empty_response"
        explanation = "The provider returned no structured response content."
        retryable = False
    elif error_class == "AIValidationError" and any(
        token in lowered for token in ("evidence id", "evidence reference", "hallucinated")
    ):
        category = "evidence_reference_validation"
        explanation = "The result cited evidence IDs that failed validation."
        retryable = False
    elif error_class in {"AIValidationError", "ValidationError", "JSONDecodeError"}:
        category = "structured_output_validation"
        explanation = "The provider response did not satisfy the structured output contract."
        retryable = False
    elif error_class == "AIProviderError":
        category = "provider_error"
        explanation = "The provider request failed; sensitive details were suppressed."
        retryable = False
    elif error_class == "TypeError":
        category = "state_or_type_mismatch"
        explanation = "A graph stage received data in an incompatible shape."
        retryable = False
    elif error_class == "ValueError":
        category = "validation_or_configuration_error"
        explanation = "A graph stage rejected a value; sensitive details were suppressed."
        retryable = False
    else:
        category = "stage_error"
        explanation = "An investigation stage failed; sensitive details were suppressed."
        retryable = False

    diagnostic: dict[str, Any] = {
        "exception_class": error_class,
        "failure_category": (
            category
            if error_class == "AIValidationError"
            and category == "evidence_reference_validation"
            else getattr(error, "category", None) or category
        ),
        "explanation": explanation,
        "retryable": bool(getattr(error, "retryable", retryable)),
        "attempt_count": int(getattr(error, "attempt_count", 1)),
    }
    for field in (
        "status_code",
        "provider_code",
        "retry_after_seconds",
        "http_status",
    ):
        value = getattr(error, field, None)
        if value is not None:
            diagnostic[field] = value
    if isinstance(error, ValidationError):
        safe_errors = error.errors(include_input=False, include_context=False, include_url=False)
        paths = sorted({".".join(str(part) for part in item.get("loc", ())) for item in safe_errors})
        if paths:
            diagnostic["schema_fields"] = paths[:5]
    else:
        paths = getattr(error, "schema_fields", None)
        if paths:
            diagnostic["schema_fields"] = [str(path)[:100] for path in paths[:5]]
    return diagnostic