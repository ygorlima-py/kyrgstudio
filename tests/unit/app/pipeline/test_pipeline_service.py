"""Unit tests for pipeline service orchestration.

These tests verify the service coordinates input normalization, job creation,
file storage, upload marking, and queueing without touching real infrastructure.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from app.pipeline.service import PipelineService
from app.queue.base import QueueBase
from app.schemas.pipeline import CopyAnalysisPipelineInput, PipelineStartResult
from app.storage.base import StorageBase, StoredFile
from app.store.base import JobStoreBase


def test_start_from_upload_creates_job_saves_file_marks_uploaded_and_enqueues() -> None:
    """Upload startup should execute the expected orchestration order."""

    events: list[str] = []
    store = JobStoreFake(events)
    storage = StorageFake(events)
    queue = QueueFake(events)
    service = PipelineService(job_store=store, storage=storage, queue=queue)

    result = _run_async(
        service.start_from_upload(
            user_id=7,
            pipeline_input=_copy_analysis_input(),
            filename="video.mp4",
            file=BytesIO(b"video-bytes"),
        )
    )

    assert result.job_id == 10
    assert events == ["create_job", "save_upload", "mark_uploaded", "enqueue"]
    assert storage.upload_calls == [
        {
            "content": b"video-bytes",
            "destination_key": "jobs/10/input.mp4",
        }
    ]
    assert store.mark_uploaded_calls == [
        {
            "job_id": 10,
            "payload": {
                "storage_backend": "fake",
                "input_file_key": "jobs/10/input.mp4",
                "input_file_uri": "fake://jobs/10/input.mp4",
            },
        }
    ]
    assert queue.enqueue_calls == [10]


def test_start_from_file_creates_job_saves_file_marks_uploaded_and_enqueues() -> None:
    """File startup should store an existing file before queueing the job."""

    events: list[str] = []
    store = JobStoreFake(events)
    storage = StorageFake(events)
    queue = QueueFake(events)
    service = PipelineService(job_store=store, storage=storage, queue=queue)

    result = _run_async(
        service.start_from_file(
            user_id=7,
            pipeline_input=_copy_analysis_input(),
            source_path="/tmp/input.wav",
        )
    )

    assert result.job_id == 10
    assert events == ["create_job", "save_file", "mark_uploaded", "enqueue"]
    assert storage.file_calls == [
        {
            "source_path": Path("/tmp/input.wav"),
            "destination_key": "jobs/10/input.wav",
        }
    ]
    assert queue.enqueue_calls == [10]


def test_start_from_upload_returns_pipeline_start_result() -> None:
    """Upload startup should return the API-facing initial pipeline result."""

    events: list[str] = []
    service = PipelineService(
        job_store=JobStoreFake(events),
        storage=StorageFake(events),
        queue=QueueFake(events),
    )

    result = _run_async(
        service.start_from_upload(
            user_id=7,
            pipeline_input=_copy_analysis_input(run_id="run_api"),
            filename="video.mp4",
            file=BytesIO(b"video-bytes"),
        )
    )

    assert isinstance(result, PipelineStartResult)
    assert result.to_dict() == {
        "job_id": 10,
        "run_id": "run_api",
        "status": "uploaded",
        "current_step": "uploaded",
        "pipeline_type": "copy_analysis",
        "storage_backend": "fake",
        "input_file_key": "jobs/10/input.mp4",
        "input_file_uri": "fake://jobs/10/input.mp4",
    }


def test_marks_job_failed_when_upload_fails_after_job_creation() -> None:
    """Upload storage failure should mark the already-created job as failed."""

    events: list[str] = []
    store = JobStoreFake(events)
    service = PipelineService(
        job_store=store,
        storage=StorageFake(events, upload_error=UploadFailure("upload failed")),
        queue=QueueFake(events),
    )

    with pytest.raises(UploadFailure):
        _run_async(
            service.start_from_upload(
                user_id=7,
                pipeline_input=_copy_analysis_input(),
                filename="video.mp4",
                file=BytesIO(b"video-bytes"),
            )
        )

    assert events == ["create_job", "save_upload", "mark_failed"]
    assert store.mark_failed_calls[0]["job_id"] == 10
    assert store.mark_failed_calls[0]["error"]["code"] == "pipeline_execution_failed"


def test_marks_job_failed_when_mark_uploaded_fails() -> None:
    """mark_uploaded failure should move the job to failed before re-raising."""

    events: list[str] = []
    store = JobStoreFake(
        events,
        mark_uploaded_error=MarkUploadedFailure("mark uploaded failed"),
    )
    service = PipelineService(
        job_store=store,
        storage=StorageFake(events),
        queue=QueueFake(events),
    )

    with pytest.raises(MarkUploadedFailure):
        _run_async(
            service.start_from_upload(
                user_id=7,
                pipeline_input=_copy_analysis_input(),
                filename="video.mp4",
                file=BytesIO(b"video-bytes"),
            )
        )

    assert events == ["create_job", "save_upload", "mark_uploaded", "mark_failed"]
    assert store.mark_failed_calls[0]["job_id"] == 10


def test_marks_job_failed_when_enqueue_fails() -> None:
    """Queue failure should mark the uploaded job as failed."""

    events: list[str] = []
    store = JobStoreFake(events)
    service = PipelineService(
        job_store=store,
        storage=StorageFake(events),
        queue=QueueFake(events, enqueue_error=EnqueueFailure("queue failed")),
    )

    with pytest.raises(EnqueueFailure):
        _run_async(
            service.start_from_upload(
                user_id=7,
                pipeline_input=_copy_analysis_input(),
                filename="video.mp4",
                file=BytesIO(b"video-bytes"),
            )
        )

    assert events == [
        "create_job",
        "save_upload",
        "mark_uploaded",
        "enqueue",
        "mark_failed",
    ]
    assert store.mark_failed_calls[0]["job_id"] == 10


def test_enqueue_failure_is_re_raised() -> None:
    """The service should not hide the original enqueue exception."""

    events: list[str] = []
    enqueue_error = EnqueueFailure("queue unavailable")
    service = PipelineService(
        job_store=JobStoreFake(events),
        storage=StorageFake(events),
        queue=QueueFake(events, enqueue_error=enqueue_error),
    )

    with pytest.raises(EnqueueFailure) as error:
        _run_async(
            service.start_from_upload(
                user_id=7,
                pipeline_input=_copy_analysis_input(),
                filename="video.mp4",
                file=BytesIO(b"video-bytes"),
            )
        )

    assert error.value is enqueue_error


class JobStoreFake(JobStoreBase):
    """JobStore fake that records calls and can fail specific transitions."""

    def __init__(
        self,
        events: list[str],
        *,
        mark_uploaded_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.mark_uploaded_error = mark_uploaded_error
        self.create_job_calls: list[dict[str, Any]] = []
        self.mark_uploaded_calls: list[dict[str, Any]] = []
        self.mark_failed_calls: list[dict[str, Any]] = []
        self.run_id: str | None = None

    async def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.events.append("create_job")
        self.create_job_calls.append(payload)
        self.run_id = payload.get("run_id")
        return {
            "id": 10,
            "run_id": self.run_id,
            "status": "pending",
            "current_step": "created",
        }

    async def mark_uploaded(
        self,
        job_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.events.append("mark_uploaded")
        self.mark_uploaded_calls.append(
            {
                "job_id": job_id,
                "payload": payload,
            }
        )

        if self.mark_uploaded_error is not None:
            raise self.mark_uploaded_error

        return {
            "id": job_id,
            "run_id": self.run_id,
            "status": "uploaded",
            "current_step": "uploaded",
            **payload,
        }

    async def mark_running(self, job_id: int, step: str) -> dict[str, Any]:
        return {"id": job_id, "status": "running", "step": step}

    async def mark_step_completed(
        self,
        job_id: int,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"id": job_id, "step": step, "payload": payload}

    async def mark_completed(
        self,
        job_id: int,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        return {"id": job_id, "status": "completed", "output": output}

    async def mark_failed(
        self,
        job_id: int,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        self.events.append("mark_failed")
        self.mark_failed_calls.append(
            {
                "job_id": job_id,
                "error": error,
            }
        )
        return {"id": job_id, "status": "failed", "error": error}

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        return None

    async def get_job_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        return None

    async def list_user_jobs(
        self,
        user_id: int,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return []


class StorageFake(StorageBase):
    """Storage fake that records calls and can fail save operations."""

    backend = "fake"

    def __init__(
        self,
        events: list[str],
        *,
        upload_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.upload_error = upload_error
        self.upload_calls: list[dict[str, object]] = []
        self.file_calls: list[dict[str, object]] = []
        self.download_calls: list[dict[str, object]] = []

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        self.events.append("save_file")
        self.file_calls.append(
            {
                "source_path": source_path,
                "destination_key": destination_key,
            }
        )
        return self._stored_file(destination_key)

    def save_upload(
        self,
        file: BinaryIO,
        destination_key: str,
    ) -> StoredFile:
        self.events.append("save_upload")
        self.upload_calls.append(
            {
                "content": file.read(),
                "destination_key": destination_key,
            }
        )

        if self.upload_error is not None:
            raise self.upload_error

        return self._stored_file(destination_key)

    def download_file(self, key: str, destination_path: Path) -> Path:
        self.download_calls.append(
            {
                "key": key,
                "destination_path": destination_path,
            }
        )
        return destination_path

    def exists(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> None:
        return None

    def uri(self, key: str) -> str:
        return f"fake://{key}"

    def delete_prefix(self, prefix: str) -> None:
        return None

    def _stored_file(self, key: str) -> StoredFile:
        return StoredFile(
            key=key,
            uri=self.uri(key),
            backend=self.backend,
        )


class QueueFake(QueueBase):
    """Queue fake that records enqueue calls and can fail on demand."""

    def __init__(
        self,
        events: list[str],
        *,
        enqueue_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.enqueue_error = enqueue_error
        self.enqueue_calls: list[int] = []

    async def enqueue(self, job_id: int) -> None:
        self.events.append("enqueue")
        self.enqueue_calls.append(job_id)

        if self.enqueue_error is not None:
            raise self.enqueue_error


class UploadFailure(RuntimeError):
    """Controlled test exception for upload failures."""


class MarkUploadedFailure(RuntimeError):
    """Controlled test exception for mark_uploaded failures."""


class EnqueueFailure(RuntimeError):
    """Controlled test exception for queue failures."""


def _copy_analysis_input(**overrides: Any) -> CopyAnalysisPipelineInput:
    """Build a valid copy analysis pipeline input."""

    payload: dict[str, Any] = {
        "source_type": "video",
        "run_id": "run_123",
        "language": "pt-BR",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "deepseek/deepseek-v4-flash",
        "max_duration_seconds": 300,
        "output_formats": ["json"],
    }
    payload.update(overrides)

    return CopyAnalysisPipelineInput(**payload)


def _run_async(awaitable: Any) -> Any:
    """Run a coroutine in unit tests without requiring pytest-asyncio."""

    return asyncio.run(awaitable)
