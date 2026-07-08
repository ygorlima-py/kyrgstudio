"""Queue contracts for application jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod


class QueueBase(ABC):
    """Base contract for job queues.

    The queue receives a job id and schedules it for execution.
    Implementations may run the job inline, send it to Celery, Redis, SQS,
    or any other backend.
    """

    @abstractmethod
    async def enqueue(self, job_id: int) -> None:
        """Schedule a job for execution."""
        ...