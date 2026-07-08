"""Unit tests for structured-output error formatting helpers."""

from __future__ import annotations

import json
from typing import Literal

import pytest
from pydantic import BaseModel, ValidationError

from kyrg.llms.error import (
    StructuredOutputParsingError,
    build_retry_prompt,
    format_structured_error,
    format_validation_error,
)


class Item(BaseModel):
    """Nested item used to create dotted validation paths."""

    value: int


class Payload(BaseModel):
    """Schema used to generate nested and literal validation errors."""

    items: list[Item]
    mode: Literal["safe", "fast"]


def _payload_error(data: object) -> ValidationError:
    """Validate data and return the generated Pydantic error."""
    with pytest.raises(ValidationError) as exc_info:
        Payload.model_validate(data)

    return exc_info.value


def test_format_validation_error_includes_required_fields() -> None:
    """Convert Pydantic errors into the compact retry payload."""
    error = _payload_error({})

    formatted = format_validation_error(error)

    assert formatted[0] == {
        "path": "items",
        "type": "missing",
        "message": "Field required",
        "invalid_value": {},
        "constraints": None,
    }
    assert formatted[1]["path"] == "mode"
    assert formatted[1]["type"] == "missing"


def test_format_validation_error_joins_nested_paths() -> None:
    """Represent nested list/index paths with dot notation."""
    error = _payload_error({"items": [{}], "mode": "wrong"})

    formatted = format_validation_error(error)
    paths = {item["path"] for item in formatted}

    assert "items.0.value" in paths
    literal_error = next(item for item in formatted if item["path"] == "mode")
    assert literal_error["type"] == "literal_error"
    assert literal_error["invalid_value"] == "wrong"
    assert literal_error["constraints"] is not None


def test_format_structured_error_delegates_validation_error() -> None:
    """Use the validation formatter for Pydantic validation failures."""
    error = _payload_error({})

    assert format_structured_error(error) == format_validation_error(error)


def test_format_structured_error_converts_parsing_error() -> None:
    """Represent non-Pydantic parsing failures with a root path."""
    error = StructuredOutputParsingError("provider returned malformed data")

    assert format_structured_error(error) == [
        {
            "path": "$",
            "type": "parsing_error",
            "message": "provider returned malformed data",
            "invalid_value": None,
            "constraints": None,
        }
    ]


def test_build_retry_prompt_contains_original_prompt_errors_and_rules() -> None:
    """Build a complete retry prompt with source prompt and JSON errors."""
    errors = [
        {
            "path": "items.0.value",
            "type": "missing",
            "message": "Field required",
            "invalid_value": {},
            "constraints": None,
        }
    ]

    prompt = build_retry_prompt("Analyze this transcript", errors)

    assert "Analyze this transcript" in prompt
    assert "<schema_validation_retry>" in prompt
    assert json.dumps(errors, ensure_ascii=False, indent=2) in prompt
    assert "Correct every listed schema violation." in prompt
    assert "Do not invent new information." in prompt
