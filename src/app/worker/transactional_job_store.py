"""Short-lived transaction adapter for worker job persistence.

``SQLAlchemyJobStore`` intentionally leaves transaction ownership to its
caller. This adapter applies that contract to background execution: each job
state change uses an independent transaction, so database resources are never
kept open while a workflow performs transcription, FFmpeg processing, or LLM
calls.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.store.database import (
    SessionFactory,
    async_session_scope,
    async_transaction_scope,
)
from app.store.jobs import SQLAlchemyJobStore
from app.store.models import Job


class WorkerJobStoreBase(Protocol):
    """Persistence operations used by ``WorkerRunner``."""

    async def get_job(self, job_id: int) -> Job | None:
        ...

    async def mark_running(self, job_id: int, step: str) -> Job:
        ...

    async def mark_completed(
        self,
        job_id: int,
        output: dict[str, Any],
    ) -> Job:
        ...

    async def mark_failed(
        self,
        job_id: int,
        error: dict[str, Any],
    ) -> Job:
        ...


class WorkerJobStore:
    """Persist worker job state through short, independent transactions.

    This class is intentionally scoped to the worker. It does not replace the
    application-wide ``SQLAlchemyJobStore`` and does not change its
    caller-controlled transaction contract.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Create the adapter using the application's async session factory."""

        self.session_factory = session_factory

    async def get_job(self, job_id: int) -> Job | None:
        """Load one job in a short-lived read session."""

        async with async_session_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).get_job(job_id)

    async def mark_running(self, job_id: int, step: str) -> Job:
        """Atomically persist the ``uploaded -> running`` transition."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).mark_running(job_id, step)

    async def mark_completed(
        self,
        job_id: int,
        output: dict[str, Any],
    ) -> Job:
        """Persist final workflow output in an independent transaction."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).mark_completed(
                job_id,
                output,
            )

    async def mark_failed(
        self,
        job_id: int,
        error: dict[str, Any],
    ) -> Job:
        """Persist a terminal worker failure in an independent transaction."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).mark_failed(
                job_id,
                error,
            )


__all__ = ["WorkerJobStore", "WorkerJobStoreBase"]
