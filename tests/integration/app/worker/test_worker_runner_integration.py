"""Integration tests for persisted worker runner behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import WorkflowResultError
from app.schemas.workflow import WorkflowExecutionRequest, WorkflowExecutionResult
from app.storage.base import StorageBase, StoredFile
from app.storage.local import LocalStorage
from app.store.factory import create_store
from app.store.jobs import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    SQLAlchemyJobStore,
)
from app.worker.materializer import StorageFileMaterializer
from app.worker.runner import WorkerRunner
from app.worker.transactional_job_store import WorkerJobStore


def test_runner_completes_uploaded_job_with_committed_checkpoints_and_local_cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Runner should persist each terminal checkpoint around workflow execution."""

    async def scenario() -> None:
        storage = LocalStorage(tmp_path / "storage")
        job_id, input_key = await _create_uploaded_job(
            session_factory=session_factory,
            storage=storage,
        )
        statuses_seen_during_execution: list[str] = []

        async def observe_running_status(
            request: WorkflowExecutionRequest,
        ) -> None:
            observed_job = await _load_job(session_factory, request.job_id)
            assert observed_job is not None
            statuses_seen_during_execution.append(observed_job.status)

        executor = WorkflowExecutorFake(on_execute=observe_running_status)
        runner = WorkerRunner(
            job_store=WorkerJobStore(session_factory),
            storage=storage,
            workflow_executor=executor,
            clock=ClockFake(10.0, 13.5),
        )

        result = await runner.run(job_id)
        persisted_job = await _load_job(session_factory, job_id)

        assert result.status == JOB_STATUS_COMPLETED
        assert result.execution_time_seconds == 3.5
        assert statuses_seen_during_execution == ["running"]
        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_COMPLETED
        assert persisted_job.output_json == {
            "transcription": {"text": "A transcript."},
            "copy_analysis": {"language": "en"},
            "token_usage": {
                "input_tokens": 8,
                "output_tokens": 5,
                "total_tokens": 13,
            },
            "execution_time_seconds": 3.5,
        }
        assert persisted_job.token_usage_json == {
            "input_tokens": 8,
            "output_tokens": 5,
            "total_tokens": 13,
        }
        assert persisted_job.execution_time_seconds == 3.5
        assert storage.exists(input_key) is False

    _run_async(scenario())


def test_runner_persists_failed_status_and_controlled_error_on_executor_failure(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Executor failures should be persisted before they are re-raised."""

    async def scenario() -> None:
        storage = LocalStorage(tmp_path / "storage")
        job_id, input_key = await _create_uploaded_job(
            session_factory=session_factory,
            storage=storage,
        )
        failure = WorkflowFailure("workflow provider failed")
        runner = WorkerRunner(
            job_store=WorkerJobStore(session_factory),
            storage=storage,
            workflow_executor=WorkflowExecutorFake(error=failure),
        )

        with pytest.raises(WorkflowFailure) as error:
            await runner.run(job_id)

        persisted_job = await _load_job(session_factory, job_id)

        assert error.value is failure
        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_FAILED
        assert persisted_job.error_json == {
            "code": "pipeline_execution_failed",
            "step": "running_pipeline",
            "details": {"error_type": "WorkflowFailure"},
        }
        assert storage.exists(input_key) is False

    _run_async(scenario())


def test_runner_materializes_and_cleans_remote_input_copy(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Remote inputs should be downloaded for execution and cleaned afterward."""

    async def scenario() -> None:
        storage = RemoteStorageFake()
        job_id, input_key = await _create_uploaded_job(
            session_factory=session_factory,
            storage=storage,
        )
        executor = WorkflowExecutorFake()
        workspace_root = tmp_path / "workspaces"
        materializer = StorageFileMaterializer(
            storage,
            workspace_root=workspace_root,
        )
        runner = WorkerRunner(
            job_store=WorkerJobStore(session_factory),
            storage=storage,
            workflow_executor=executor,
            file_resolver=materializer,
        )

        await runner.run(job_id)

        assert storage.download_calls == [input_key]
        assert executor.source_contents == [b"source-video"]
        assert list(workspace_root.iterdir()) == []
        assert storage.deleted_prefixes == [f"jobs/{job_id}/"]

    _run_async(scenario())


def test_duplicate_delivery_does_not_execute_completed_job_twice(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """A duplicate delivery should reject terminal jobs before workflow execution."""

    async def scenario() -> None:
        storage = LocalStorage(tmp_path / "storage")
        job_id, _ = await _create_uploaded_job(
            session_factory=session_factory,
            storage=storage,
        )
        executor = WorkflowExecutorFake()
        runner = WorkerRunner(
            job_store=WorkerJobStore(session_factory),
            storage=storage,
            workflow_executor=executor,
        )

        await runner.run(job_id)

        with pytest.raises(WorkflowResultError) as error:
            await runner.run(job_id)

        persisted_job = await _load_job(session_factory, job_id)

        assert error.value.details["status"] == JOB_STATUS_COMPLETED
        assert len(executor.requests) == 1
        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_COMPLETED

    _run_async(scenario())


class WorkflowExecutorFake:
    """Workflow executor fake used while persistence and storage stay real."""

    def __init__(
        self,
        *,
        error: Exception | None = None,
        on_execute: (
            Callable[[WorkflowExecutionRequest], Awaitable[None]] | None
        ) = None,
    ) -> None:
        self.error = error
        self.on_execute = on_execute
        self.requests: list[WorkflowExecutionRequest] = []
        self.source_contents: list[bytes] = []

    async def execute(
        self,
        request: WorkflowExecutionRequest,
    ) -> WorkflowExecutionResult:
        self.requests.append(request)
        self.source_contents.append(request.source_path.read_bytes())

        if self.on_execute is not None:
            await self.on_execute(request)

        if self.error is not None:
            raise self.error

        return WorkflowExecutionResult(
            output_json={
                "transcription": {"text": "A transcript."},
                "copy_analysis": {"language": "en"},
            },
            token_usage={
                "input_tokens": 8,
                "output_tokens": 5,
                "total_tokens": 13,
            },
        )


class RemoteStorageFake(StorageBase):
    """In-memory remote storage fake with real temporary downloads."""

    backend = "remote"

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.download_calls: list[str] = []
        self.deleted_prefixes: list[str] = []

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        self.files[destination_key] = source_path.read_bytes()
        return self._stored_file(destination_key)

    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        self.files[destination_key] = file.read()
        return self._stored_file(destination_key)

    def download_file(self, key: str, destination_path: Path) -> Path:
        self.download_calls.append(key)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(self.files[key])
        return destination_path

    def exists(self, key: str) -> bool:
        return key in self.files

    def delete(self, key: str) -> None:
        self.files.pop(key, None)

    def uri(self, key: str) -> str:
        return f"remote://{key}"

    def delete_prefix(self, prefix: str) -> None:
        self.deleted_prefixes.append(prefix)

        for key in list(self.files):
            if key.startswith(prefix):
                self.files.pop(key)

    def _stored_file(self, key: str) -> StoredFile:
        return StoredFile(key=key, uri=self.uri(key), backend=self.backend)


class ClockFake:
    """Deterministic monotonic clock used for persisted duration checks."""

    def __init__(self, *values: float) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


class WorkflowFailure(RuntimeError):
    """Workflow error used to verify persisted failure behavior."""


async def _create_uploaded_job(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    storage: StorageBase,
) -> tuple[int, str]:
    """Create a real user and uploaded job backed by the given storage."""

    async with session_factory.begin() as session:
        store = create_store(session)
        user = await store.users.create_user(
            {
                "email": f"worker-{uuid4().hex}@example.com",
                "password_hash": "hashed-password",
            }
        )
        job = await store.jobs.create_job(
            {
                "user_id": user.id,
                "run_id": f"worker-run-{uuid4().hex}",
                "pipeline_type": "copy_analysis",
                "input_json": {"source_type": "video"},
            }
        )
        input_key = f"jobs/{job.id}/input.mp4"
        stored_file = storage.save_upload(BytesIO(b"source-video"), input_key)
        await store.jobs.mark_uploaded(
            job.id,
            {
                "storage_backend": stored_file.backend,
                "input_file_key": stored_file.key,
                "input_file_uri": stored_file.uri,
            },
        )

    return job.id, input_key


async def _load_job(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
) -> Any:
    """Load a persisted job through a fresh real SQLAlchemy session."""

    async with session_factory() as session:
        return await SQLAlchemyJobStore(session).get_job(job_id)


def _run_async(awaitable: Awaitable[Any]) -> Any:
    """Run one async integration scenario from a synchronous pytest test."""

    return asyncio.run(awaitable)
