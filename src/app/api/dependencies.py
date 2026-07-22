"""Typed FastAPI dependencies for API application resources.

Long-lived resources are created by the API lifespan and stored in application
state. This module validates and adapts those resources for request handlers.
Database sessions remain request-scoped, while pipeline submission uses its
own short transaction boundaries through ``PipelineJobStore``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.dependencies import get_current_user
from app.errors import ProviderConfigError
from app.pipeline.service import PipelineService
from app.pipeline.transactional_job_store import PipelineJobStore
from app.queue.base import QueueBase
from app.settings import AppSettings
from app.storage.base import StorageBase
from app.store.base import JobStoreBase
from app.store.database import (
    SessionFactory,
    async_session_scope,
)
from app.store.jobs import SQLAlchemyJobStore


def get_settings(request: Request) -> AppSettings:
    """Return the validated settings created for this API process."""

    settings = getattr(request.app.state, "settings", None)

    if not isinstance(settings, AppSettings):
        raise _missing_api_resource("settings")

    return settings


def get_session_factory(request: Request) -> SessionFactory:
    """Return the shared factory used to create short database sessions."""

    session_factory = getattr(request.app.state, "session_factory", None)

    if not isinstance(session_factory, async_sessionmaker):
        raise _missing_api_resource("session_factory")

    return session_factory


def get_storage(request: Request) -> StorageBase:
    """Return the storage backend initialized by the API lifespan."""

    storage = getattr(request.app.state, "storage", None)

    if not isinstance(storage, StorageBase):
        raise _missing_api_resource("storage")

    return storage


def get_queue(request: Request) -> QueueBase:
    """Return the queue adapter initialized by the API lifespan."""

    queue = getattr(request.app.state, "queue", None)

    if not isinstance(queue, QueueBase):
        raise _missing_api_resource("queue")

    return queue


async def get_session(
    session_factory: Annotated[
        SessionFactory,
        Depends(get_session_factory),
    ],
) -> AsyncIterator[AsyncSession]:
    """Yield one read-scoped session and close it after the response."""

    async with async_session_scope(session_factory) as session:
        yield session


def get_job_store(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobStoreBase:
    """Build the job read store over the current request session."""

    return SQLAlchemyJobStore(session)


def get_pipeline_service(
    session_factory: Annotated[
        SessionFactory,
        Depends(get_session_factory),
    ],
    storage: Annotated[StorageBase, Depends(get_storage)],
    queue: Annotated[QueueBase, Depends(get_queue)],
) -> PipelineService:
    """Build the submission facade from transaction-safe dependencies."""

    return PipelineService(
        job_store=PipelineJobStore(session_factory),
        storage=storage,
        queue=queue,
    )


def _missing_api_resource(resource_name: str) -> ProviderConfigError:
    return ProviderConfigError(
        technical_message=(
            f"API resource is not configured in application state: "
            f"{resource_name}"
        ),
        step="configuring_api",
        details={"resource": resource_name},
    )


__all__ = [
    "get_current_user",
    "get_job_store",
    "get_pipeline_service",
    "get_queue",
    "get_session",
    "get_session_factory",
    "get_settings",
    "get_storage",
]
