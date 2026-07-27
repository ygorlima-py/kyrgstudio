"""Output normalization for worker workflow results.

Workflows may return Pydantic models, dataclasses, plain dictionaries, or a
``WorkflowExecutionResult`` wrapper. The database should receive only stable,
JSON-serializable dictionaries. This module owns that conversion so the runner
does not mix execution control with output shaping.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.errors import WorkflowResultError
from app.schemas.pipeline import PipelineType
from app.schemas.workflow import WorkflowExecutionResult


TOKEN_USAGE_KEYS = ("input_tokens", "output_tokens", "total_tokens")
ADAPTED_SCRIPT_RESULT_FIELDS = frozenset(
    {
        "validation_errors",
        "validation_passed",
        "validation_warnings",
        "missing_proofs",
    }
)


def build_completed_output(
    *,
    pipeline_type: PipelineType,
    result: WorkflowExecutionResult | Mapping[str, Any] | BaseModel,
    execution_time_seconds: float,
) -> dict[str, Any]:
    """Build the final JSON payload persisted by ``JobStore.mark_completed``.

    Args:
        pipeline_type: Pipeline executed by the worker.
        result: Raw workflow result or normalized workflow execution result.
        execution_time_seconds: Total measured worker execution time.

    Returns:
        A stable, JSON-serializable dictionary ready to be saved in the job.

    Raises:
        WorkflowResultError: If the pipeline type is unsupported or the final
            payload cannot be serialized as JSON.
    """

    payload, token_usage = normalize_workflow_result(result)
    normalized_execution_time = _normalize_execution_time(execution_time_seconds)

    if pipeline_type == "copy_analysis":
        output = build_copy_analysis_output(
            payload=payload,
            token_usage=token_usage,
            execution_time_seconds=normalized_execution_time,
        )
    elif pipeline_type == "copy_adaptation":
        output = build_copy_adaptation_output(
            payload=payload,
            token_usage=token_usage,
            execution_time_seconds=normalized_execution_time,
        )
    else:
        raise WorkflowResultError(
            technical_message="Unsupported pipeline type for worker output.",
            step="building_output",
            details={"pipeline_type": pipeline_type},
        )

    return ensure_json_serializable(output)


def normalize_workflow_result(
    result: WorkflowExecutionResult | Mapping[str, Any] | BaseModel,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert a workflow result into payload and token usage dictionaries."""

    if isinstance(result, WorkflowExecutionResult):
        payload = _json_safe(result.output_json)
        token_usage = _json_safe(result.token_usage)
    elif isinstance(result, BaseModel):
        payload = _json_safe(result)
        token_usage = extract_token_usage(payload)
    elif isinstance(result, Mapping):
        payload = _json_safe(result)
        token_usage = extract_token_usage(payload)
    else:
        raise WorkflowResultError(
            technical_message="Unsupported workflow result type.",
            step="building_output",
            details={"result_type": result.__class__.__name__},
        )

    if not isinstance(payload, dict):
        raise WorkflowResultError(
            technical_message="Workflow result payload must be an object.",
            step="building_output",
            details={"result_type": result.__class__.__name__},
        )

    if not isinstance(token_usage, dict):
        token_usage = {}

    return payload, token_usage


def build_copy_analysis_output(
    *,
    payload: Mapping[str, Any],
    token_usage: Mapping[str, Any],
    execution_time_seconds: float,
) -> dict[str, Any]:
    """Build the persisted output for a copy-analysis pipeline."""

    return {
        "transcription": _public_transcription(payload),
        "copy_analysis": _first_present(
            payload,
            "copy_analysis",
            "analysis",
        ),
        "token_usage": dict(token_usage),
        "execution_time_seconds": execution_time_seconds,
    }


def build_copy_adaptation_output(
    *,
    payload: Mapping[str, Any],
    token_usage: Mapping[str, Any],
    execution_time_seconds: float,
) -> dict[str, Any]:
    """Build the persisted output for a copy-adaptation pipeline."""

    adapted_script = _first_present(
        payload,
        "adapted_script",
        "script",
    )

    return {
        "transcription": _public_transcription(payload),
        "copy_analysis": _first_present(
            payload,
            "copy_analysis",
            "analysis",
        ),
        "adapted_script": _adapted_script_content(adapted_script),
        "validation": _first_present(payload, "validation"),
        "missing_proofs": _missing_proofs(payload, adapted_script),
        "token_usage": dict(token_usage),
        "execution_time_seconds": execution_time_seconds,
    }


def _public_transcription(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return only transcription fields that belong to the final product."""

    transcription = _first_present(
        payload,
        "transcription",
        "transcriber",
        "transcriber_result",
        "result",
    )

    if transcription is None:
        return None

    normalized_transcription = _json_safe(transcription)

    if not isinstance(normalized_transcription, Mapping):
        raise WorkflowResultError(
            technical_message="Workflow transcription must be an object.",
            step="building_output",
            details={
                "transcription_type": transcription.__class__.__name__,
            },
        )

    return {
        key: normalized_transcription[key]
        for key in ("language", "text")
        if key in normalized_transcription
    }


def _adapted_script_content(adapted_script: Any) -> dict[str, Any] | None:
    """Return script content without duplicated result-level diagnostics.

    Validation and proof diagnostics have canonical top-level locations in the
    persisted pipeline output. Removing their nested copies keeps one source of
    truth while preserving every field used to render or edit the script.
    """

    if adapted_script is None:
        return None

    normalized_script = _json_safe(adapted_script)

    if not isinstance(normalized_script, Mapping):
        raise WorkflowResultError(
            technical_message="Adapted script output must be an object.",
            step="building_output",
            details={
                "adapted_script_type": adapted_script.__class__.__name__,
            },
        )

    return {
        key: value
        for key, value in normalized_script.items()
        if key not in ADAPTED_SCRIPT_RESULT_FIELDS
    }


def extract_token_usage(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Extract token usage from a workflow payload.

    The preferred shape is ``{"token_usage": {...}}``. The fallback supports
    workflow states that expose ``input_tokens``, ``output_tokens``, and
    ``total_tokens`` at the top level.
    """

    token_usage = payload.get("token_usage")

    if isinstance(token_usage, Mapping):
        return dict(_json_safe(token_usage))

    top_level_usage = {
        key: payload[key]
        for key in TOKEN_USAGE_KEYS
        if key in payload and payload[key] is not None
    }

    return _json_safe(top_level_usage)


def ensure_json_serializable(output: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe dictionary or raise a controlled workflow error."""

    json_safe_output = _json_safe(output)

    try:
        json.dumps(json_safe_output)
    except TypeError as error:
        raise WorkflowResultError(
            technical_message="Worker output is not JSON serializable.",
            step="building_output",
            details={"error_type": error.__class__.__name__},
        ) from error

    return json_safe_output


def _missing_proofs(
    payload: Mapping[str, Any],
    adapted_script: Any,
) -> list[Any]:
    missing_proofs = payload.get("missing_proofs")

    if isinstance(missing_proofs, list):
        return missing_proofs

    if isinstance(adapted_script, Mapping):
        nested_missing_proofs = adapted_script.get("missing_proofs")

        if isinstance(nested_missing_proofs, list):
            return nested_missing_proofs

    return []


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]

    return None


def _normalize_execution_time(value: float) -> float:
    return round(max(float(value), 0.0), 6)


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, set):
        return [_json_safe(item) for item in value]

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime | date):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    return value


__all__ = [
    "ADAPTED_SCRIPT_RESULT_FIELDS",
    "TOKEN_USAGE_KEYS",
    "build_completed_output",
    "build_copy_adaptation_output",
    "build_copy_analysis_output",
    "ensure_json_serializable",
    "extract_token_usage",
    "normalize_workflow_result",
]
