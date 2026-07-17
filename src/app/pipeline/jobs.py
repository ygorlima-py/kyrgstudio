"""Job payload helpers for the pipeline application layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.errors import AppError, InvalidInputError, PipelineExecutionError
from app.pipeline.files import PipelineInputFile
from app.pipeline.input import PipelineInput, PipelineType, get_pipeline_type
from app.pipeline.transactional_job_store import PipelineJobStoreBase


async def create_pipeline_job(
    *,
    job_store: PipelineJobStoreBase,
    user_id: int,
    pipeline_input: PipelineInput,
) -> Any:
    """Create a pending job from a normalized pipeline input."""

    payload = build_create_job_payload(
        user_id=user_id,
        pipeline_input=pipeline_input,
    )
    return await job_store.create_job(payload)


async def mark_pipeline_job_uploaded(
    *,
    job_store: PipelineJobStoreBase,
    job_id: int,
    input_file: PipelineInputFile,
) -> Any:
    """Persist stored input file references and move the job to uploaded."""

    return await job_store.mark_uploaded(
        job_id,
        build_uploaded_job_payload(input_file),
    )


async def mark_pipeline_job_failed(
    *,
    job_store: PipelineJobStoreBase,
    job_id: int,
    error: AppError | Exception | Mapping[str, Any],
) -> Any:
    """Persist a controlled pipeline error and move the job to failed."""

    return await job_store.mark_failed(
        job_id,
        build_failed_job_payload(error),
    )


def build_create_job_payload(
    *,
    user_id: int,
    pipeline_input: PipelineInput,
) -> dict[str, Any]:
    """Build the payload expected by ``JobStore.create_job``."""

    pipeline_type = get_pipeline_type(pipeline_input)

    return {
        "user_id": _normalize_user_id(user_id, pipeline_type=pipeline_type),
        "pipeline_type": pipeline_type,
        "run_id": pipeline_input.run_id,
        "input_json": build_input_json(pipeline_input),
    }


def build_uploaded_job_payload(
    input_file: PipelineInputFile,
) -> dict[str, str]:
    """Build the payload expected by ``JobStore.mark_uploaded``."""

    return input_file.to_job_payload()


def build_failed_job_payload(
    error: AppError | Exception | Mapping[str, Any],
) -> dict[str, Any]:
    """Build the payload expected by ``JobStore.mark_failed``."""

    if isinstance(error, AppError):
        return error.to_dict()

    if isinstance(error, Mapping):
        return dict(error)

    return PipelineExecutionError(
        technical_message="Pipeline execution failed.",
        details={"error_type": error.__class__.__name__},
    ).to_dict()


def build_input_json(pipeline_input: PipelineInput) -> dict[str, Any]:
    """Serialize pipeline input into a JSON-compatible database payload."""

    if isinstance(pipeline_input, BaseModel):
        return pipeline_input.model_dump(mode="json")

    raise InvalidInputError(
        technical_message="Pipeline input must be a Pydantic model.",
        details={"input_type": type(pipeline_input).__name__},
    )


def _normalize_user_id(
    user_id: int,
    *,
    pipeline_type: PipelineType,
) -> int:
    if isinstance(user_id, bool):
        raise _invalid_user_id(user_id, pipeline_type=pipeline_type)

    try:
        normalized_user_id = int(user_id)
    except (TypeError, ValueError) as error:
        raise _invalid_user_id(user_id, pipeline_type=pipeline_type) from error

    if normalized_user_id <= 0:
        raise _invalid_user_id(user_id, pipeline_type=pipeline_type)

    return normalized_user_id


def _invalid_user_id(
    user_id: object,
    *,
    pipeline_type: PipelineType,
) -> InvalidInputError:
    return InvalidInputError(
        technical_message="user_id must be a positive integer.",
        details={
            "field": "user_id",
            "value": user_id,
            "pipeline_type": pipeline_type,
        },
    )


__all__ = [
    "build_create_job_payload",
    "build_failed_job_payload",
    "build_input_json",
    "build_uploaded_job_payload",
    "create_pipeline_job",
    "mark_pipeline_job_failed",
    "mark_pipeline_job_uploaded",
]
