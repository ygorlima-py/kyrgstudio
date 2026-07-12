"""Celery entry points for persisted pipeline jobs.

Tasks receive only a job identifier. They build task-scoped infrastructure and
delegate all job execution, state transitions, and cleanup to ``WorkerRunner``.
"""

from __future__ import annotations

import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine

from app.settings import load_settings
from app.storage.factory import create_storage
from app.store.database import (
    create_async_engine_from_settings,
    create_async_session_factory,
    dispose_async_engine,
)
from app.worker.celery_app import (
    PIPELINE_TASK_NAME,
    celery_app,
)
from app.worker.runner import WorkerRunner
from app.worker.transactional_job_store import WorkerJobStore
from app.worker.workflows import KyrgWorkflowExecutor


@celery_app.task(
    name=PIPELINE_TASK_NAME,
    ignore_result=True,
)
def run_pipeline_job(job_id: int) -> None:
    """Execute one already-uploaded pipeline job through the worker runner."""

    asyncio.run(_run_pipeline_job(job_id))


async def _run_pipeline_job(job_id: int) -> None:
    """Create task-scoped dependencies and delegate execution to the runner."""

    settings = load_settings()
    engine = create_async_engine_from_settings(settings)

    try:
        session_factory = create_async_session_factory(engine)
        job_store = WorkerJobStore(session_factory)
        storage = create_storage(settings)
        workflow_executor = KyrgWorkflowExecutor(settings=settings)

        runner = WorkerRunner(
            job_store=job_store,
            storage=storage,
            workflow_executor=workflow_executor,
        )
        await runner.run(job_id)
    finally:
        await _dispose_engine_safely(engine, job_id=job_id)


async def _dispose_engine_safely(engine: AsyncEngine, *, job_id: int) -> None:
    """Release task-owned database resources without replacing job outcomes."""

    try:
        await dispose_async_engine(engine)
    except Exception:
        logger.exception(
            "Failed to dispose database engine for worker job_id={}",
            job_id,
        )


__all__ = ["run_pipeline_job"]
