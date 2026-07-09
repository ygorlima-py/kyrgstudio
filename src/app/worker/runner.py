"""Worker runner for executing already-created pipeline jobs.

The runner is the app-level boundary between persisted jobs and workflow
execution. It does not receive uploads, create jobs, configure Celery, or know
HTTP concerns. It receives dependencies, loads an uploaded job, executes the
proper workflow through an injected executor, and persists the final state.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from app.errors import (
    AppError,
    PipelineExecutionError,
    StorageError,
    WorkflowResultError,
)
from app.schemas.pipeline import PipelineType
from app.schemas.workflow import (
    ResolvedInputFile,
    WorkflowExecutionRequest,
    WorkflowExecutionResult,
    WorkerRunResult,
)
from app.storage.base import StorageBase
from app.store.base import JobStoreBase


JOB_STATUS_UPLOADED = "uploaded"
RUNNING_STEP = "running_pipeline"


class WorkerFileResolver(Protocol):
    """Resolves a stored input file into a local path for workflows."""

    def resolve(self, job: Any) -> ResolvedInputFile:
        ...

    def cleanup(self, resolved_file: ResolvedInputFile) -> None:
        ...


class WorkflowExecutor(Protocol):
    """Executes the workflow required by a job."""

    async def execute(
        self,
        request: WorkflowExecutionRequest,
    ) -> WorkflowExecutionResult | Mapping[str, Any] | BaseModel:
        ...


class StorageInputResolver:
    """Default resolver for storage backends that expose a local file path.

    Remote storage backends will need ``materializer.py`` to download the
    object before execution. Until that module exists, this resolver safely
    supports local storage and fails with a controlled storage error otherwise.
    """

    def __init__(self, storage: StorageBase) -> None:
        self.storage = storage

    def resolve(self, job: Any) -> ResolvedInputFile:
        storage_backend = _job_required_str(job, "storage_backend")
        input_file_key = _job_required_str(job, "input_file_key")
        input_file_uri = _job_required_str(job, "input_file_uri")

        if not self.storage.exists(input_file_key):
            raise StorageError(
                technical_message="Stored input file does not exist.",
                step="materializing_input",
                details={
                    "storage_backend": storage_backend,
                    "input_file_key": input_file_key,
                    "input_file_uri": input_file_uri,
                },
            )

        if storage_backend != "local":
            raise StorageError(
                technical_message=(
                    "Remote storage input requires a materializer before "
                    "workflow execution."
                ),
                step="materializing_input",
                details={
                    "storage_backend": storage_backend,
                    "input_file_key": input_file_key,
                },
            )

        local_path = Path(self.storage.uri(input_file_key))

        if not local_path.is_file():
            raise StorageError(
                technical_message="Resolved input path is not a file.",
                step="materializing_input",
                details={
                    "storage_backend": storage_backend,
                    "input_file_key": input_file_key,
                    "local_path": str(local_path),
                },
            )

        return ResolvedInputFile(
            storage_backend=storage_backend,
            input_file_key=input_file_key,
            input_file_uri=input_file_uri,
            local_path=local_path,
            should_cleanup=False,
        )

    def cleanup(self, resolved_file: ResolvedInputFile) -> None:
        """No-op for local storage; remote materializers may delete downloads."""

        return None


class WorkerRunner:
    """Execute one queued job and persist its final state."""

    def __init__(
        self,
        *,
        job_store: JobStoreBase,
        storage: StorageBase,
        workflow_executor: WorkflowExecutor,
        file_resolver: WorkerFileResolver | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.job_store = job_store
        self.storage = storage
        self.workflow_executor = workflow_executor
        self.file_resolver = file_resolver or StorageInputResolver(storage)
        self.clock = clock

    async def run(self, job_id: int) -> WorkerRunResult:
        """Run an uploaded job through its workflow pipeline."""

        normalized_job_id = _normalize_job_id(job_id)
        job = await self.job_store.get_job(normalized_job_id)

        if job is None:
            raise WorkflowResultError(
                technical_message="Job was not found.",
                step="loading_job",
                details={"job_id": normalized_job_id},
            )

        _ensure_job_is_uploaded(job)
        running_job = await self.job_store.mark_running(
            normalized_job_id,
            RUNNING_STEP,
        )

        resolved_file: ResolvedInputFile | None = None
        started_at = self.clock()

        try:
            resolved_file = self.file_resolver.resolve(running_job)
            request = _build_execution_request(
                job=running_job,
                resolved_file=resolved_file,
            )
            workflow_result = await self.workflow_executor.execute(request)
            execution_time_seconds = _elapsed_seconds(self.clock() - started_at)
            completed_output = _build_completed_output(
                workflow_result,
                execution_time_seconds=execution_time_seconds,
            )
            completed_job = await self.job_store.mark_completed(
                normalized_job_id,
                completed_output,
            )

            return WorkerRunResult(
                job_id=normalized_job_id,
                status=_job_required_str(completed_job, "status"),
                pipeline_type=request.pipeline_type,
                execution_time_seconds=execution_time_seconds,
            )
        except Exception as error:
            await self._mark_failed_safely(
                job_id=normalized_job_id,
                error=error,
            )
            raise
        finally:
            if resolved_file is not None:
                self._cleanup_safely(resolved_file)

    async def _mark_failed_safely(
        self,
        *,
        job_id: int,
        error: AppError | Exception,
    ) -> None:
        try:
            await self.job_store.mark_failed(job_id, _error_payload(error))
        except Exception:
            return

    def _cleanup_safely(self, resolved_file: ResolvedInputFile) -> None:
        try:
            self.file_resolver.cleanup(resolved_file)
        except Exception:
            return


def _build_execution_request(
    *,
    job: Any,
    resolved_file: ResolvedInputFile,
) -> WorkflowExecutionRequest:
    input_json = _job_mapping(job, "input_json")

    return WorkflowExecutionRequest(
        job_id=_job_id(job),
        pipeline_type=_pipeline_type(_job_required_str(job, "pipeline_type")),
        source_path=resolved_file.local_path,
        source_type=_required_input_str(input_json, "source_type"),
        input_json=input_json,
    )


def _build_completed_output(
    result: WorkflowExecutionResult | Mapping[str, Any] | BaseModel,
    *,
    execution_time_seconds: float,
) -> dict[str, Any]:
    if isinstance(result, WorkflowExecutionResult):
        output = dict(result.output_json)
        token_usage = dict(result.token_usage)
    elif isinstance(result, BaseModel):
        output = result.model_dump(mode="json")
        token_usage = _optional_mapping(output.get("token_usage"))
    else:
        output = dict(result)
        token_usage = _optional_mapping(output.get("token_usage"))

    output["token_usage"] = token_usage
    output["execution_time_seconds"] = execution_time_seconds

    return _json_safe(output)


def _ensure_job_is_uploaded(job: Any) -> None:
    status = _job_required_str(job, "status")

    if status != JOB_STATUS_UPLOADED:
        raise WorkflowResultError(
            technical_message="Job is not ready for worker execution.",
            step="loading_job",
            details={
                "job_id": _job_id(job),
                "status": status,
                "required_status": JOB_STATUS_UPLOADED,
            },
        )


def _pipeline_type(value: str) -> PipelineType:
    if value == "copy_analysis":
        return "copy_analysis"

    if value == "copy_adaptation":
        return "copy_adaptation"

    raise WorkflowResultError(
        technical_message="Unsupported job pipeline type.",
        step="loading_job",
        details={"pipeline_type": value},
    )


def _required_input_str(input_json: Mapping[str, Any], field: str) -> str:
    value = input_json.get(field)

    if value is None or str(value).strip() == "":
        raise WorkflowResultError(
            technical_message="Required job input field is missing.",
            step="loading_job",
            details={"field": field},
        )

    return str(value).strip()


def _error_payload(error: AppError | Exception) -> dict[str, Any]:
    if isinstance(error, AppError):
        return error.to_dict()

    return PipelineExecutionError(
        technical_message="Worker execution failed.",
        step=RUNNING_STEP,
        details={"error_type": error.__class__.__name__},
    ).to_dict()


def _job_id(job: Any) -> int:
    return _normalize_job_id(_job_value(job, "id"))


def _normalize_job_id(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError("Job id must be an integer.")

    try:
        normalized_value = int(value)
    except (TypeError, ValueError) as error:
        raise TypeError("Job id must be an integer.") from error

    if normalized_value <= 0:
        raise TypeError("Job id must be a positive integer.")

    return normalized_value


def _job_required_str(job: Any, field: str) -> str:
    value = _job_value(job, field)

    if value is None or str(value).strip() == "":
        raise WorkflowResultError(
            technical_message="Required job field is missing.",
            step="loading_job",
            details={"field": field, "job_id": _safe_job_id(job)},
        )

    return str(value).strip()


def _job_mapping(job: Any, field: str) -> dict[str, Any]:
    value = _job_value(job, field)

    if not isinstance(value, Mapping):
        raise WorkflowResultError(
            technical_message="Required job field must be an object.",
            step="loading_job",
            details={"field": field, "job_id": _safe_job_id(job)},
        )

    return dict(value)


def _job_value(job: Any, field: str) -> Any:
    if isinstance(job, Mapping):
        return job.get(field)

    return getattr(job, field, None)


def _safe_job_id(job: Any) -> int | None:
    try:
        return _job_id(job)
    except Exception:
        return None


def _optional_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    return {}


def _elapsed_seconds(value: float) -> float:
    return round(max(value, 0.0), 6)


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, Path):
        return str(value)

    return value


__all__ = [
    "JOB_STATUS_UPLOADED",
    "RUNNING_STEP",
    "ResolvedInputFile",
    "StorageInputResolver",
    "WorkerFileResolver",
    "WorkerRunResult",
    "WorkerRunner",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResult",
    "WorkflowExecutor",
]
