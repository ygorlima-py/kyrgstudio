"""Pipeline orchestration service for the application layer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from app.errors import AppError
from app.pipeline.files import (
    PipelineInputFile,
    save_pipeline_file,
    save_pipeline_upload,
)
from app.pipeline.input import (
    PipelineInput,
    PipelineType,
    get_pipeline_type,
    normalize_pipeline_input,
)
from app.pipeline.jobs import (
    create_pipeline_job,
    mark_pipeline_job_failed,
    mark_pipeline_job_uploaded,
)
from app.queue.base import QueueBase
from app.storage.base import StorageBase
from app.store.base import JobStoreBase
from app.schemas.pipeline import PipelineStartResult


class PipelineService:
    """Application facade used to create, upload, and enqueue pipeline jobs."""

    def __init__(
        self,
        *,
        job_store: JobStoreBase,
        storage: StorageBase,
        queue: QueueBase,
    ) -> None:
        self.job_store = job_store
        self.storage = storage
        self.queue = queue

    async def start_from_upload(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        filename: str,
        file: BinaryIO,
    ) -> PipelineStartResult:
        """Create a job, save an uploaded stream, and enqueue processing."""

        return await self._start(
            user_id=user_id,
            pipeline_input=pipeline_input,
            save_input_file=lambda job_id: save_pipeline_upload(
                storage=self.storage,
                job_id=job_id,
                filename=filename,
                file=file,
            ),
        )

    async def start_from_file(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        source_path: Path | str,
        filename: str | None = None,
    ) -> PipelineStartResult:
        """Create a job, save an existing local file, and enqueue processing."""

        resolved_filename = filename or Path(source_path).name

        return await self._start(
            user_id=user_id,
            pipeline_input=pipeline_input,
            save_input_file=lambda job_id: save_pipeline_file(
                storage=self.storage,
                job_id=job_id,
                filename=resolved_filename,
                source_path=source_path,
            ),
        )

    async def _start(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        save_input_file: Callable[[int], PipelineInputFile],
    ) -> PipelineStartResult:
        normalized_input = normalize_pipeline_input(pipeline_input)
        pipeline_type = get_pipeline_type(normalized_input)

        job = await create_pipeline_job(
            job_store=self.job_store,
            user_id=user_id,
            pipeline_input=normalized_input,
        )
        job_id = _job_id(job)

        try:
            input_file = save_input_file(job_id)
            uploaded_job = await mark_pipeline_job_uploaded(
                job_store=self.job_store,
                job_id=job_id,
                input_file=input_file,
            )
            await self.queue.enqueue(job_id)
        except Exception as error:
            await self._mark_failed_safely(job_id=job_id, error=error)
            raise

        return PipelineStartResult(
            job_id=job_id,
            run_id=_job_optional_str(uploaded_job, "run_id"),
            status=_job_required_str(uploaded_job, "status"),
            current_step=_job_optional_str(uploaded_job, "current_step"),
            pipeline_type=pipeline_type,
            storage_backend=input_file.storage_backend,
            input_file_key=input_file.input_file_key,
            input_file_uri=input_file.input_file_uri,
        )

    async def _mark_failed_safely(
        self,
        *,
        job_id: int,
        error: AppError | Exception,
    ) -> None:
        try:
            await mark_pipeline_job_failed(
                job_store=self.job_store,
                job_id=job_id,
                error=error,
            )
        except Exception:
            return


def _job_id(job: Any) -> int:
    value = _job_value(job, "id")

    if isinstance(value, bool):
        raise TypeError("Job id must be an integer.")

    return int(value)


def _job_required_str(job: Any, field: str) -> str:
    value = _job_value(job, field)

    if value is None or str(value).strip() == "":
        raise TypeError(f"Job field is required: {field}")

    return str(value)


def _job_optional_str(job: Any, field: str) -> str | None:
    value = _job_value(job, field)

    if value is None:
        return None

    normalized_value = str(value).strip()
    return normalized_value or None


def _job_value(job: Any, field: str) -> Any:
    if isinstance(job, dict):
        return job.get(field)

    return getattr(job, field)


__all__ = [
    "PipelineService",
    "PipelineStartResult",
]
