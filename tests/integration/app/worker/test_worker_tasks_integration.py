"""Integration tests for the Celery task boundary."""

from __future__ import annotations

from typing import Any

import pytest

import app.worker.tasks as tasks
from app.worker.celery_app import celery_app


def test_celery_task_runs_eagerly_with_fake_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Celery task should construct and invoke a runner in eager mode."""

    captured: dict[str, Any] = {}
    sentinel_engine = object()
    sentinel_session_factory = object()
    sentinel_storage = object()
    original_eager = celery_app.conf.task_always_eager
    original_propagates = celery_app.conf.task_eager_propagates

    class WorkerJobStoreFake:
        def __init__(self, session_factory: object) -> None:
            captured["session_factory"] = session_factory

    class WorkflowExecutorFake:
        def __init__(self, *, settings: object) -> None:
            captured["settings"] = settings

    class WorkerRunnerFake:
        def __init__(
            self,
            *,
            job_store: object,
            storage: object,
            workflow_executor: object,
        ) -> None:
            captured["job_store"] = job_store
            captured["storage"] = storage
            captured["workflow_executor"] = workflow_executor

        async def run(self, job_id: int) -> None:
            captured["job_id"] = job_id

    async def fake_dispose(engine: object, *, job_id: int) -> None:
        captured["disposed_engine"] = engine
        captured["disposed_job_id"] = job_id

    monkeypatch.setattr(tasks, "create_async_engine_from_settings", lambda _: sentinel_engine)
    monkeypatch.setattr(
        tasks,
        "create_async_session_factory",
        lambda _: sentinel_session_factory,
    )
    monkeypatch.setattr(tasks, "create_storage", lambda _: sentinel_storage)
    monkeypatch.setattr(tasks, "WorkerJobStore", WorkerJobStoreFake)
    monkeypatch.setattr(tasks, "KyrgWorkflowExecutor", WorkflowExecutorFake)
    monkeypatch.setattr(tasks, "WorkerRunner", WorkerRunnerFake)
    monkeypatch.setattr(tasks, "_dispose_engine_safely", fake_dispose)

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

    try:
        result = tasks.run_pipeline_job.delay(41)
    finally:
        celery_app.conf.update(
            task_always_eager=original_eager,
            task_eager_propagates=original_propagates,
        )

    assert result.successful() is True
    assert captured["job_id"] == 41
    assert captured["session_factory"] is sentinel_session_factory
    assert captured["storage"] is sentinel_storage
    assert captured["disposed_engine"] is sentinel_engine
    assert captured["disposed_job_id"] == 41
