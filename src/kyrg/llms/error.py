"""Error types and retry-prompt helpers for structured LLM output.

The LLM adapters normalize provider-specific parsing and validation failures
into a small set of project-level exceptions. Workflows can then handle
structured-output failures consistently without knowing whether the underlying
provider was OpenAI, Gemini, LangChain, or another SDK.
"""

import json
from pydantic import ValidationError


class StructuredOutputError(RuntimeError):
    """Raised when structured output remains invalid after all retry attempts."""

    pass


class StructuredOutputParsingError(RuntimeError):
    """Raised when a provider cannot produce a parseable structured object."""


def format_validation_error(error: ValidationError) -> list[dict]:
    """Convert a Pydantic validation error into retry-friendly dictionaries.

    Args:
        error: Validation error raised while validating provider output against
            a Pydantic schema.

    Returns:
        A list of dictionaries containing the invalid field path, error type,
        human-readable message, invalid input value, and validation
        constraints when available.

    Example:
        A nested location like ``("items", 0, "name")`` is serialized as
        ``"items.0.name"`` so it can be embedded cleanly in retry prompts.
    """
    return [
        {
            "path": ".".join(map(str, item["loc"])),
            "type": item["type"],
            "message": item["msg"],
            "invalid_value": item.get("input"),
            "constraints": item.get("ctx"),
        }
        for item in error.errors()
    ]


def format_structured_error(
    error: ValidationError | StructuredOutputParsingError,
) -> list[dict]:
    """Normalize supported structured-output errors into one payload shape.

    Args:
        error: Pydantic validation error or provider parsing error.

    Returns:
        A list of error dictionaries suitable for ``build_retry_prompt``.
    """
    if isinstance(error, ValidationError):
        return format_validation_error(error)

    return [
        {
            "path": "$",
            "type": "parsing_error",
            "message": str(error),
            "invalid_value": None,
            "constraints": None,
        }
    ]

def build_retry_prompt(
    original_prompt: str,
    errors: list[dict],
) -> str:
    """Build the prompt used for a structured-output retry attempt.

    Args:
        original_prompt: The first prompt sent to the provider.
        errors: Formatted schema or parsing errors from the failed attempt.

    Returns:
        A prompt containing the original task plus a dedicated retry block with
        serialized validation errors and correction rules.

    Design:
        The retry prompt keeps the original prompt intact and appends error
        context in a tagged block. This reduces the chance that retry metadata
        overwrites the original task while still making schema violations
        explicit.
    """
    return f"""
{original_prompt}

<schema_validation_retry>
Your previous response failed schema validation.

Validation errors:
{json.dumps(errors, ensure_ascii=False, indent=2)}

Return the complete output again.
Correct every listed schema violation.
Preserve all previously valid information.
Do not invent new information.
</schema_validation_retry>
"""
