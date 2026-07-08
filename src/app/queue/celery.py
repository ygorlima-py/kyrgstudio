"""Celery queue implementation for background job execution."""

from __future__ import annotations

from typing import Protocol

from app.errors import PipelineExecutionError
from app.queue.base import QueueBase


class CeleryTask(Protocol):
    """Minimal Celery task contract used by CeleryQueue."""

    def delay(self, job_id: int) -> object:
        ...


class CeleryQueue(QueueBase):
    """Queue implementation that schedules jobs through Celery.

    This class does not execute the pipeline. It only sends the job id to a
    Celery task so a worker process can execute it separately.
    """

    def __init__(self, task: CeleryTask) -> None:
        self.task = task

    async def enqueue(self, job_id: int) -> None:
        """Schedule a job for execution by a Celery worker."""

        try:
            self.task.delay(job_id)
        except Exception as error:
            raise PipelineExecutionError(
                technical_message=f"Failed to enqueue job in Celery: {error}",
                step="enqueue_job",
                details={"job_id": job_id},
            ) from error