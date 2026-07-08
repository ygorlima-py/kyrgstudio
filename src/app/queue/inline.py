"""Inline queue implementation for local execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.queue.base import QueueBase


JobHandler = Callable[[int], Awaitable[None]]


class InlineQueue(QueueBase):
    """Queue implementation that runs the job handler immediately.

    Useful for local development and simple MVP execution without Redis,
    Celery, SQS, or a separate worker process.
    """

    def __init__(self, handler: JobHandler) -> None:
        self.handler = handler

    async def enqueue(self, job_id: int) -> None:
        """Execute the job immediately in the current process."""
        await self.handler(job_id)