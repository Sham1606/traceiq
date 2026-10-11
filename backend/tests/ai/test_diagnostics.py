"""Safe error diagnostics must not expose arbitrary exception values."""

from pydantic import BaseModel, ValidationError

from app.ai.diagnostics import safe_error_diagnostic
from app.ai.validation import AIValidationError


def test_evidence_reference_diagnostics_do_not_include_rejected_ids():
    rejected_id = "private-value-must-not-appear"
    diagnostic = safe_error_diagnostic(
        AIValidationError(f"Invalid or hallucinated evidence ID: {rejected_id}")
    )

    assert diagnostic["failure_category"] == "evidence_reference_validation"
    assert diagnostic["exception_class"] == "AIValidationError"
    assert rejected_id not in str(diagnostic)


def test_schema_diagnostics_include_only_safe_field_paths():
    class RequiredOutput(BaseModel):
        hypothesis_id: str

    try:
        RequiredOutput.model_validate({"secret_value": "private-value-must-not-appear"})
    except ValidationError as error:
        diagnostic = safe_error_diagnostic(error)

    assert diagnostic["failure_category"] == "structured_output_validation"
    assert diagnostic["schema_fields"] == ["hypothesis_id"]
    assert "private-value-must-not-appear" not in str(diagnostic)


def test_unknown_stage_error_is_bounded_and_does_not_copy_exception_text():
    diagnostic = safe_error_diagnostic(RuntimeError("private request body and headers"))

    assert diagnostic["failure_category"] == "stage_error"
    assert diagnostic["explanation"] == "An investigation stage failed; sensitive details were suppressed."
    assert "private request body" not in str(diagnostic)