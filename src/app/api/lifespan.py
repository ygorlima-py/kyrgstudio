"""Application lifecycle management for the HTTP API.

The API owns long-lived infrastructure required to submit jobs. It never owns
workflow execution: jobs are delegated to Celery and executed by a separate
worker process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from fastapi import FastAPI

from app.queue.base import QueueBase
from app.queue.celery import CeleryQueue, CeleryTask
from app.settings import load_settings
from app.storage.factory import create_storage
from app.store.database import (
    create_async_engine_from_settings,
    create_async_session_factory,
    dispose_async_engine,
)


@asynccontextmanager
async def api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and release API-scoped infrastructure.

    Sessions remain request-scoped and are created later from the stored
    ``SessionFactory``. No job is submitted and no workflow is executed while
    the API starts or stops.
    """

    settings = load_settings()
    engine = create_async_engine_from_settings(settings)

    try:
        session_factory = create_async_session_factory(engine)
        storage = create_storage(settings)
        queue = _create_pipeline_queue()

        app.state.settings = settings
        app.state.session_factory = session_factory
        app.state.storage = storage
        app.state.queue = queue

        yield
    finally:
        await dispose_async_engine(engine)


def _create_pipeline_queue() -> QueueBase:
    """Create the queue adapter without executing workflow code."""

    # Importing the Celery task registers its message entry point only. The
    # task body and all workflows run later in a Celery worker process.
    from app.worker.tasks import run_pipeline_job

    return CeleryQueue(cast(CeleryTask, run_pipeline_job))


__all__ = ["api_lifespan"]
