"""Durable database checkpoints for pipeline job submission.

``SQLAlchemyJobStore`` deliberately leaves transaction ownership to its caller.
This adapter applies that rule to job submission: each persisted checkpoint is
committed before the pipeline advances to storage or queue scheduling.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.store.database import SessionFactory, async_transaction_scope
from app.store.jobs import SQLAlchemyJobStore
from app.store.models import Job


class PipelineJobStoreBase(Protocol):
    """Persistence operations required by ``PipelineService``."""

    async def create_job(self, payload: dict[str, Any]) -> Job:
        """Create and durably persist a pending job."""

        ...

    async def mark_uploaded(self, job_id: int, payload: dict[str, Any]) -> Job:
        """Persist storage references and the uploaded state."""

        ...

    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Job:
        """Persist a controlled submission failure."""

        ...


class PipelineJobStore:
    """Persist pipeline submission checkpoints in short transactions.

    The adapter is used by API or CLI composition code. It does not replace the
    general-purpose ``SQLAlchemyJobStore`` and does not handle file storage or
    queue scheduling.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Create the adapter from the application's async session factory."""

        self.session_factory = session_factory

    async def create_job(self, payload: dict[str, Any]) -> Job:
        """Create a pending job and commit it before file upload starts."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).create_job(payload)

    async def mark_uploaded(self, job_id: int, payload: dict[str, Any]) -> Job:
        """Commit uploaded storage references before queue scheduling."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).mark_uploaded(
                job_id,
                payload,
            )

    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Job:
        """Commit a controlled submission failure in its own transaction."""

        async with async_transaction_scope(self.session_factory) as session:
            return await SQLAlchemyJobStore(session).mark_failed(job_id, error)


__all__ = ["PipelineJobStore", "PipelineJobStoreBase"]
