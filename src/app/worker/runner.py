"""Worker runner for executing already-created pipeline jobs.

The runner is the app-level boundary between persisted jobs and workflow
execution. It does not receive uploads, create jobs, configure Celery, or know
HTTP concerns. It receives dependencies, loads an uploaded job, executes the
proper workflow through an injected executor, and persists the final state.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from loguru import logger
from pydantic import BaseModel

from app.errors import (
    AppError,
    PipelineExecutionError,
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
from app.storage.paths import job_prefix
from app.worker.materializer import StorageFileMaterializer
from app.worker.outputs import build_completed_output
from app.worker.transactional_job_store import WorkerJobStoreBase

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


class WorkerRunner:
    """Execute one queued job and persist its final state."""

    def __init__(
        self,
        *,
        job_store: WorkerJobStoreBase,
        storage: StorageBase,
        workflow_executor: WorkflowExecutor,
        file_resolver: WorkerFileResolver | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.job_store = job_store
        self.storage = storage
        self.workflow_executor = workflow_executor
        self.file_resolver = file_resolver or StorageFileMaterializer(storage)
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
        terminal_state_persisted = False
        started_at = self.clock()

        try:
            resolved_file = self.file_resolver.resolve(running_job)
            request = _build_execution_request(
                job=running_job,
                resolved_file=resolved_file,
            )
            workflow_result = await self.workflow_executor.execute(request)
            execution_time_seconds = _elapsed_seconds(self.clock() - started_at)
            completed_output = build_completed_output(
                pipeline_type=request.pipeline_type,
                result=workflow_result,
                execution_time_seconds=execution_time_seconds,
            )
            completed_job = await self.job_store.mark_completed(
                normalized_job_id,
                completed_output,
            )
            terminal_state_persisted = True

            return WorkerRunResult(
                job_id=normalized_job_id,
                status=_job_required_str(completed_job, "status"),
                pipeline_type=request.pipeline_type,
                execution_time_seconds=execution_time_seconds,
            )
        except Exception as error:
            failure_persisted = await self._mark_failed_safely(
                job_id=normalized_job_id,
                error=error,
            )
            terminal_state_persisted = (
                terminal_state_persisted or failure_persisted
            )
            raise
        finally:
            if resolved_file is not None:
                self._cleanup_safely(resolved_file)

            if terminal_state_persisted:
                self._delete_job_files_safely(normalized_job_id)

    async def _mark_failed_safely(
        self,
        *,
        job_id: int,
        error: AppError | Exception,
    ) -> bool:
        try:
            await self.job_store.mark_failed(job_id, _error_payload(error))
        except Exception:
            logger.exception(
                "Failed to persist terminal failure state for job_id={}",
                job_id,
            )
            return False

        return True

    def _cleanup_safely(self, resolved_file: ResolvedInputFile) -> None:
        try:
            self.file_resolver.cleanup(resolved_file)
        except Exception:
            logger.exception(
                "Failed to clean materialized input for key={}",
                resolved_file.input_file_key,
            )

    def _delete_job_files_safely(self, job_id: int) -> None:
        prefix = job_prefix(str(job_id))

        try:
            self.storage.delete_prefix(prefix)
        except Exception:
            logger.exception(
                "Failed to delete stored files for job_id={} prefix={}",
                job_id,
                prefix,
            )


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


def _elapsed_seconds(value: float) -> float:
    return round(max(value, 0.0), 6)


__all__ = [
    "JOB_STATUS_UPLOADED",
    "RUNNING_STEP",
    "ResolvedInputFile",
    "WorkerFileResolver",
    "WorkerRunResult",
    "WorkerRunner",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResult",
    "WorkflowExecutor",
]
