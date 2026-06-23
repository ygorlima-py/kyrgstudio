import json
from pydantic import ValidationError


class StructuredOutputError(RuntimeError):
    pass


class StructuredOutputParsingError(RuntimeError):
    """Structured response could not be parsed into a valid object."""


def format_validation_error(error: ValidationError) -> list[dict]:
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
