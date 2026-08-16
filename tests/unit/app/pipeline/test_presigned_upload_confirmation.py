"""Tests for confirming objects uploaded directly to object storage."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from app.errors import FileNotFoundAppError, InvalidInputError, JobNotFoundError
from app.pipeline.service import PipelineService
from app.pipeline.transactional_job_store import PipelineJobStoreBase
from app.queue.base import QueueBase
from app.storage.base import StorageBase, StoredObjectMetadata


def test_confirmation_marks_matching_object_as_uploaded() -> None:
    store = ConfirmationJobStore(_pending_job())
    storage = ConfirmationStorage(
        StoredObjectMetadata(
            key="jobs/10/input.mp4",
            size_bytes=11,
            content_type="video/mp4",
        )
    )
    queue = QueueSpy()
    service = _service(store, storage, queue)

    result = _run(service.confirm_presigned_upload(user_id=7, job_id=10))

    assert result.status == "uploaded"
    assert result.input_file_key == "jobs/10/input.mp4"
    assert store.mark_uploaded_payload == {
        "storage_backend": "r2",
        "input_file_key": "jobs/10/input.mp4",
        "input_file_uri": "r2://jobs/10/input.mp4",
    }
    assert queue.calls == [10]


def test_confirmation_rejects_missing_object_without_mutating_job() -> None:
    store = ConfirmationJobStore(_pending_job())
    service = _service(store, ConfirmationStorage(None))

    with pytest.raises(FileNotFoundAppError):
        _run(service.confirm_presigned_upload(user_id=7, job_id=10))

    assert store.mark_uploaded_payload is None


@pytest.mark.parametrize(
    "metadata",
    [
        StoredObjectMetadata(
            key="jobs/10/input.mp4",
            size_bytes=12,
            content_type="video/mp4",
        ),
        StoredObjectMetadata(
            key="jobs/10/input.mp4",
            size_bytes=11,
            content_type="video/quicktime",
        ),
    ],
)
def test_confirmation_rejects_object_metadata_mismatch(
    metadata: StoredObjectMetadata,
) -> None:
    store = ConfirmationJobStore(_pending_job())
    service = _service(store, ConfirmationStorage(metadata))

    with pytest.raises(InvalidInputError):
        _run(service.confirm_presigned_upload(user_id=7, job_id=10))

    assert store.mark_uploaded_payload is None


def test_confirmation_hides_jobs_owned_by_another_user() -> None:
    service = _service(
        ConfirmationJobStore(_pending_job(user_id=8)),
        ConfirmationStorage(
            StoredObjectMetadata(
                key="jobs/10/input.mp4",
                size_bytes=11,
                content_type="video/mp4",
            )
        ),
    )

    with pytest.raises(JobNotFoundError):
        _run(service.confirm_presigned_upload(user_id=7, job_id=10))


def test_confirmation_is_idempotent_after_upload() -> None:
    job = _pending_job()
    job.update(
        {
            "status": "uploaded",
            "current_step": "uploaded",
            "storage_backend": "r2",
            "input_file_key": "jobs/10/input.mp4",
            "input_file_uri": "r2://jobs/10/input.mp4",
        }
    )
    store = ConfirmationJobStore(job)
    service = _service(store, ConfirmationStorage(None))

    result = _run(service.confirm_presigned_upload(user_id=7, job_id=10))

    assert result.status == "uploaded"
    assert store.mark_uploaded_payload is None


def test_confirmation_marks_job_failed_when_queue_rejects_job() -> None:
    store = ConfirmationJobStore(_pending_job())
    queue = QueueSpy(error=RuntimeError("broker unavailable"))
    service = _service(
        store,
        ConfirmationStorage(
            StoredObjectMetadata(
                key="jobs/10/input.mp4",
                size_bytes=11,
                content_type="video/mp4",
            )
        ),
        queue,
    )

    with pytest.raises(RuntimeError, match="broker unavailable"):
        _run(service.confirm_presigned_upload(user_id=7, job_id=10))

    assert queue.calls == [10]
    assert store.mark_failed_payload is not None


class ConfirmationJobStore:
    """Minimal store fake for the confirmation lifecycle."""

    def __init__(self, job: dict[str, Any]) -> None:
        self.job = job
        self.mark_uploaded_payload: dict[str, str] | None = None
        self.mark_failed_payload: dict[str, Any] | None = None

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        return self.job if self.job["id"] == job_id else None

    async def mark_uploaded(
        self,
        job_id: int,
        payload: dict[str, str],
    ) -> dict[str, Any]:
        self.mark_uploaded_payload = payload
        self.job.update(payload, status="uploaded", current_step="uploaded")
        return self.job

    async def mark_failed(
        self,
        job_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.mark_failed_payload = payload
        self.job.update(status="failed", current_step="failed")
        return self.job


class ConfirmationStorage:
    """Storage fake exposing only the metadata contract required here."""

    backend = "r2"

    def __init__(self, metadata: StoredObjectMetadata | None) -> None:
        self.metadata = metadata

    def get_object_metadata(self, key: str) -> StoredObjectMetadata | None:
        if self.metadata is None or self.metadata.key != key:
            return None
        return self.metadata

    def uri(self, key: str) -> str:
        return f"r2://{key}"


class QueueSpy(QueueBase):
    """Queue fake proving confirmation does not enqueue processing."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[int] = []
        self.error = error

    async def enqueue(self, job_id: int) -> None:
        self.calls.append(job_id)
        if self.error is not None:
            raise self.error


def _pending_job(*, user_id: int = 7) -> dict[str, Any]:
    return {
        "id": 10,
        "user_id": user_id,
        "run_id": "run-10",
        "pipeline_type": "copy_analysis",
        "status": "pending",
        "current_step": "created",
        "storage_backend": None,
        "input_file_key": None,
        "input_file_uri": None,
        "input_json": {
            "_direct_upload": {
                "filename": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": 11,
            }
        },
    }


def _service(
    store: ConfirmationJobStore,
    storage: ConfirmationStorage,
    queue: QueueSpy | None = None,
) -> PipelineService:
    return PipelineService(
        job_store=cast(PipelineJobStoreBase, store),
        storage=cast(StorageBase, storage),
        queue=queue or QueueSpy(),
    )


def _run(awaitable: Any) -> Any:
    return asyncio.run(awaitable)
