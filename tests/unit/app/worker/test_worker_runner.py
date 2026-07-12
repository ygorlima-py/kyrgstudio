"""Unit tests for persisted worker job execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from app.errors import WorkflowResultError
from app.schemas.workflow import (
    ResolvedInputFile,
    WorkflowExecutionRequest,
    WorkflowExecutionResult,
)
from app.storage.base import StorageBase, StoredFile
from app.worker.runner import RUNNING_STEP, WorkerRunner


def test_rejects_invalid_job_id() -> None:
    """Runner should reject invalid job identifiers before accessing the store."""

    for job_id in (0, -1, True, "invalid", None):
        store = WorkerJobStoreFake(_uploaded_job())
        runner = _runner(store=store)

        with pytest.raises(TypeError):
            _run_async(runner.run(job_id))

        assert store.events == []


def test_rejects_job_not_found() -> None:
    """Runner should stop when the requested persisted job does not exist."""

    store = WorkerJobStoreFake(None)
    runner = _runner(store=store)

    with pytest.raises(WorkflowResultError) as error:
        _run_async(runner.run(7))

    assert error.value.step == "loading_job"
    assert error.value.details == {"job_id": 7}
    assert store.events == ["get_job"]


def test_rejects_job_not_uploaded() -> None:
    """Runner should not execute jobs outside the uploaded state."""

    store = WorkerJobStoreFake(_uploaded_job(status="pending"))
    executor = WorkflowExecutorFake()
    runner = _runner(store=store, executor=executor)

    with pytest.raises(WorkflowResultError) as error:
        _run_async(runner.run(7))

    assert error.value.step == "loading_job"
    assert error.value.details["status"] == "pending"
    assert store.events == ["get_job"]
    assert executor.requests == []


def test_marks_job_running_before_workflow_execution() -> None:
    """The atomic running transition must precede file and workflow work."""

    events: list[str] = []
    store = WorkerJobStoreFake(_uploaded_job(), events=events)
    resolver = FileResolverFake(events=events)
    executor = WorkflowExecutorFake(events=events)
    runner = _runner(
        store=store,
        resolver=resolver,
        executor=executor,
        storage=StorageFake(events=events),
    )

    _run_async(runner.run(7))

    assert events.index("mark_running") < events.index("resolve")
    assert events.index("mark_running") < events.index("execute")
    assert store.mark_running_calls == [{"job_id": 7, "step": RUNNING_STEP}]


def test_builds_workflow_execution_request() -> None:
    """Runner should translate the stored job and local file into one request."""

    job = _uploaded_job(
        pipeline_type="copy_adaptation",
        input_json={
            "source_type": "audio",
            "language": "pt-BR",
            "user_profile": {"product": "Course"},
        },
    )
    resolved_file = _resolved_file(local_path=Path("/tmp/input.wav"))
    executor = WorkflowExecutorFake()
    runner = _runner(
        store=WorkerJobStoreFake(job),
        resolver=FileResolverFake(resolved_file),
        executor=executor,
    )

    _run_async(runner.run(7))

    assert executor.requests == [
        WorkflowExecutionRequest(
            job_id=7,
            pipeline_type="copy_adaptation",
            source_path=Path("/tmp/input.wav"),
            source_type="audio",
            input_json={
                "source_type": "audio",
                "language": "pt-BR",
                "user_profile": {"product": "Course"},
            },
        )
    ]


def test_persists_serializable_output_and_execution_time_on_success() -> None:
    """Successful execution should persist JSON-safe output and elapsed time."""

    store = WorkerJobStoreFake(_uploaded_job())
    executor = WorkflowExecutorFake(
        result=WorkflowExecutionResult(
            output_json={
                "transcription": {"text": "A clean transcript."},
                "copy_analysis": {"language": "en"},
                "local_asset": Path("/tmp/asset.png"),
            },
            token_usage={
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
            },
        )
    )
    runner = _runner(
        store=store,
        executor=executor,
        clock=ClockFake(10.0, 12.3456789),
    )

    result = _run_async(runner.run(7))

    assert result.status == "completed"
    assert result.execution_time_seconds == 2.345679
    assert store.completed_calls == [
        {
            "job_id": 7,
            "output": {
                "transcription": {"text": "A clean transcript."},
                "copy_analysis": {"language": "en"},
                "token_usage": {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "total_tokens": 14,
                },
                "execution_time_seconds": 2.345679,
            },
        }
    ]
    json.dumps(store.completed_calls[0]["output"])


def test_persists_controlled_error_on_workflow_failure() -> None:
    """Workflow failures should be persisted as controlled job errors."""

    execution_error = WorkflowFailure("provider unavailable")
    store = WorkerJobStoreFake(_uploaded_job())
    runner = _runner(
        store=store,
        executor=WorkflowExecutorFake(error=execution_error),
    )

    with pytest.raises(WorkflowFailure) as error:
        _run_async(runner.run(7))

    assert error.value is execution_error
    assert store.failed_calls == [
        {
            "job_id": 7,
            "error": {
                "code": "pipeline_execution_failed",
                "step": RUNNING_STEP,
                "details": {"error_type": "WorkflowFailure"},
            },
        }
    ]


def test_preserves_original_error_when_mark_failed_fails() -> None:
    """Failure persistence must not replace the original workflow exception."""

    execution_error = WorkflowFailure("workflow failed")
    store = WorkerJobStoreFake(
        _uploaded_job(),
        mark_failed_error=FailurePersistenceError("database unavailable"),
    )
    resolver = FileResolverFake()
    storage = StorageFake()
    runner = _runner(
        store=store,
        resolver=resolver,
        executor=WorkflowExecutorFake(error=execution_error),
        storage=storage,
    )

    with pytest.raises(WorkflowFailure) as error:
        _run_async(runner.run(7))

    assert error.value is execution_error
    assert resolver.cleanup_calls == [resolver.resolved_file]
    assert storage.deleted_prefixes == []


def test_cleans_materialized_file_on_success() -> None:
    """Resolved inputs should be cleaned after a successful workflow run."""

    resolver = FileResolverFake()
    runner = _runner(resolver=resolver)

    _run_async(runner.run(7))

    assert resolver.cleanup_calls == [resolver.resolved_file]


def test_cleans_materialized_file_on_failure() -> None:
    """Resolved inputs should be cleaned even when workflow execution fails."""

    resolver = FileResolverFake()
    runner = _runner(
        resolver=resolver,
        executor=WorkflowExecutorFake(error=WorkflowFailure("workflow failed")),
    )

    with pytest.raises(WorkflowFailure):
        _run_async(runner.run(7))

    assert resolver.cleanup_calls == [resolver.resolved_file]


def test_deletes_job_prefix_on_success() -> None:
    """Terminal success should remove the stored files belonging to the job."""

    storage = StorageFake()
    runner = _runner(storage=storage)

    _run_async(runner.run(7))

    assert storage.deleted_prefixes == ["jobs/7/"]


def test_deletes_job_prefix_on_failure() -> None:
    """Terminal failure should remove stored job files after persisting failure."""

    storage = StorageFake()
    runner = _runner(
        storage=storage,
        executor=WorkflowExecutorFake(error=WorkflowFailure("workflow failed")),
    )

    with pytest.raises(WorkflowFailure):
        _run_async(runner.run(7))

    assert storage.deleted_prefixes == ["jobs/7/"]


class WorkerJobStoreFake:
    """Job-state fake that records runner interactions without a database."""

    def __init__(
        self,
        job: dict[str, Any] | None,
        *,
        events: list[str] | None = None,
        mark_failed_error: Exception | None = None,
    ) -> None:
        self.job = job
        self.events = events if events is not None else []
        self.mark_failed_error = mark_failed_error
        self.mark_running_calls: list[dict[str, Any]] = []
        self.completed_calls: list[dict[str, Any]] = []
        self.failed_calls: list[dict[str, Any]] = []

    async def get_job(self, job_id: int) -> Any:
        self.events.append("get_job")
        return self.job

    async def mark_running(self, job_id: int, step: str) -> Any:
        self.events.append("mark_running")
        self.mark_running_calls.append({"job_id": job_id, "step": step})

        if self.job is None:
            raise AssertionError("mark_running requires an existing job")

        return {**self.job, "status": "running", "current_step": step}

    async def mark_completed(self, job_id: int, output: dict[str, Any]) -> Any:
        self.events.append("mark_completed")
        self.completed_calls.append({"job_id": job_id, "output": output})
        return {"id": job_id, "status": "completed"}

    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Any:
        self.events.append("mark_failed")
        self.failed_calls.append({"job_id": job_id, "error": error})

        if self.mark_failed_error is not None:
            raise self.mark_failed_error

        return {"id": job_id, "status": "failed"}


class FileResolverFake:
    """File resolver fake that returns one deterministic local input file."""

    def __init__(
        self,
        resolved_file: ResolvedInputFile | None = None,
        *,
        events: list[str] | None = None,
    ) -> None:
        self.resolved_file = resolved_file or _resolved_file()
        self.events = events if events is not None else []
        self.resolve_calls: list[Any] = []
        self.cleanup_calls: list[ResolvedInputFile] = []

    def resolve(self, job: Any) -> ResolvedInputFile:
        self.events.append("resolve")
        self.resolve_calls.append(job)
        return self.resolved_file

    def cleanup(self, resolved_file: ResolvedInputFile) -> None:
        self.events.append("cleanup")
        self.cleanup_calls.append(resolved_file)


class WorkflowExecutorFake:
    """Async workflow fake with configurable result or execution failure."""

    def __init__(
        self,
        *,
        result: WorkflowExecutionResult | None = None,
        error: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.result = result or _workflow_result()
        self.error = error
        self.events = events if events is not None else []
        self.requests: list[WorkflowExecutionRequest] = []

    async def execute(
        self,
        request: WorkflowExecutionRequest,
    ) -> WorkflowExecutionResult:
        self.events.append("execute")
        self.requests.append(request)

        if self.error is not None:
            raise self.error

        return self.result


class StorageFake(StorageBase):
    """Storage fake that records job-prefix cleanup without filesystem I/O."""

    backend = "fake"

    def __init__(self, *, events: list[str] | None = None) -> None:
        self.events = events if events is not None else []
        self.deleted_prefixes: list[str] = []

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        return self._stored_file(destination_key)

    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        file.read()
        return self._stored_file(destination_key)

    def download_file(self, key: str, destination_path: Path) -> Path:
        return destination_path

    def exists(self, key: str) -> bool:
        return True

    def delete(self, key: str) -> None:
        return None

    def uri(self, key: str) -> str:
        return f"fake://{key}"

    def delete_prefix(self, prefix: str) -> None:
        self.events.append("delete_prefix")
        self.deleted_prefixes.append(prefix)

    def _stored_file(self, key: str) -> StoredFile:
        return StoredFile(key=key, uri=self.uri(key), backend=self.backend)


class ClockFake:
    """Deterministic monotonic clock for execution-duration assertions."""

    def __init__(self, *values: float) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


class WorkflowFailure(RuntimeError):
    """Workflow failure used to exercise runner error handling."""


class FailurePersistenceError(RuntimeError):
    """Failure persistence error used to preserve the original exception."""


def _runner(
    *,
    store: WorkerJobStoreFake | None = None,
    resolver: FileResolverFake | None = None,
    executor: WorkflowExecutorFake | None = None,
    storage: StorageFake | None = None,
    clock: Callable[[], float] | None = None,
) -> WorkerRunner:
    """Build a runner with deterministic fakes for one unit-test scenario."""

    return WorkerRunner(
        job_store=store or WorkerJobStoreFake(_uploaded_job()),
        storage=storage or StorageFake(),
        workflow_executor=executor or WorkflowExecutorFake(),
        file_resolver=resolver or FileResolverFake(),
        clock=clock or ClockFake(0.0, 1.0),
    )


def _uploaded_job(
    *,
    status: str = "uploaded",
    pipeline_type: str = "copy_analysis",
    input_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimum persisted job shape accepted by the runner."""

    return {
        "id": 7,
        "status": status,
        "pipeline_type": pipeline_type,
        "input_json": input_json or {"source_type": "video"},
        "storage_backend": "fake",
        "input_file_key": "jobs/7/input.mp4",
        "input_file_uri": "fake://jobs/7/input.mp4",
    }


def _resolved_file(*, local_path: Path = Path("/tmp/input.mp4")) -> ResolvedInputFile:
    """Build a local input reference returned by the file resolver fake."""

    return ResolvedInputFile(
        storage_backend="fake",
        input_file_key="jobs/7/input.mp4",
        input_file_uri="fake://jobs/7/input.mp4",
        local_path=local_path,
    )


def _workflow_result() -> WorkflowExecutionResult:
    """Build a minimal successful copy-analysis workflow result."""

    return WorkflowExecutionResult(
        output_json={
            "transcription": {"text": "Transcript"},
            "copy_analysis": {"language": "en"},
        },
        token_usage={
            "input_tokens": 3,
            "output_tokens": 2,
            "total_tokens": 5,
        },
    )


def _run_async(awaitable: Any) -> Any:
    """Run one coroutine without requiring an async pytest plugin."""

    return asyncio.run(awaitable)
