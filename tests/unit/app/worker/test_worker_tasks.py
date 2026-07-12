"""Unit tests for the public Celery worker task."""

from __future__ import annotations

import inspect

import pytest

import app.worker.tasks as tasks
from app.worker.celery_app import PIPELINE_TASK_NAME


def test_run_pipeline_job_accepts_only_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public task should forward only its persisted job identifier."""

    received_job_ids: list[int] = []

    async def fake_run_pipeline_job(job_id: int) -> None:
        received_job_ids.append(job_id)

    monkeypatch.setattr(tasks, "_run_pipeline_job", fake_run_pipeline_job)

    assert tuple(inspect.signature(tasks.run_pipeline_job.run).parameters) == (
        "job_id",
    )
    assert tasks.run_pipeline_job.name == PIPELINE_TASK_NAME

    tasks.run_pipeline_job.run(27)

    assert received_job_ids == [27]
