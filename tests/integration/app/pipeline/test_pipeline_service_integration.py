"""Integration tests for pipeline service startup behavior.

These tests use a real database session, real local storage, and the real
InlineQueue. They intentionally do not execute workflows or external providers.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Coroutine, Iterator
from io import BytesIO
from pathlib import Path
from typing import Any, Awaitable
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.pipeline.service import PipelineService
from app.queue.inline import InlineQueue
from app.schemas.pipeline import CopyAnalysisPipelineInput
from app.storage.local import LocalStorage
from app.store.factory import AppStore
from app.store.factory import create_store
from app.store.jobs import JOB_STATUS_FAILED, JOB_STATUS_UPLOADED
from app.store.models import User


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"


def test_start_from_file_creates_job_saves_local_file_marks_uploaded_and_enqueues(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """start_from_file should persist job, file references, and queue the job id."""

    async def scenario() -> None:
        queued_job_ids: list[int] = []
        source_file = tmp_path / "source.mp4"
        source_file.write_bytes(b"video-from-file")
        storage = LocalStorage(tmp_path / "storage")

        async with session_factory.begin() as session:
            store = create_store(session)
            user = await _create_user(store)
            service = PipelineService(
                job_store=store.jobs,
                storage=storage,
                queue=InlineQueue(_record_job_id(queued_job_ids)),
            )

            result = await service.start_from_file(
                user_id=user.id,
                pipeline_input=_copy_analysis_input(run_id=_run_id()),
                source_path=source_file,
            )

        async with session_factory() as session:
            store = create_store(session)
            persisted_job = await store.jobs.get_job(result.job_id)

        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_UPLOADED
        assert persisted_job.storage_backend == "local"
        assert persisted_job.input_file_key == f"jobs/{result.job_id}/input.mp4"
        assert persisted_job.input_file_uri == result.input_file_uri
        assert Path(result.input_file_uri).is_file()
        assert Path(result.input_file_uri).read_bytes() == b"video-from-file"
        assert queued_job_ids == [result.job_id]

    _run_async(scenario())


def test_start_from_upload_creates_job_saves_local_upload_marks_uploaded_and_enqueues(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """start_from_upload should store uploaded bytes and queue the job id."""

    async def scenario() -> None:
        queued_job_ids: list[int] = []
        storage = LocalStorage(tmp_path / "storage")

        async with session_factory.begin() as session:
            store = create_store(session)
            user = await _create_user(store)
            service = PipelineService(
                job_store=store.jobs,
                storage=storage,
                queue=InlineQueue(_record_job_id(queued_job_ids)),
            )

            result = await service.start_from_upload(
                user_id=user.id,
                pipeline_input=_copy_analysis_input(run_id=_run_id()),
                filename="upload.wav",
                file=BytesIO(b"upload-bytes"),
            )

        async with session_factory() as session:
            store = create_store(session)
            persisted_job = await store.jobs.get_job(result.job_id)

        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_UPLOADED
        assert persisted_job.storage_backend == "local"
        assert persisted_job.input_file_key == f"jobs/{result.job_id}/input.wav"
        assert Path(result.input_file_uri).is_file()
        assert Path(result.input_file_uri).read_bytes() == b"upload-bytes"
        assert queued_job_ids == [result.job_id]

    _run_async(scenario())


def test_pipeline_service_marks_job_failed_when_inline_queue_fails(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Queue failure should persist a failed job status with controlled error."""

    async def scenario() -> None:
        storage = LocalStorage(tmp_path / "storage")

        async with session_factory.begin() as session:
            store = create_store(session)
            user = await _create_user(store)
            run_id = _run_id()
            service = PipelineService(
                job_store=store.jobs,
                storage=storage,
                queue=InlineQueue(_failing_handler),
            )

            with pytest.raises(QueueFailure):
                await service.start_from_upload(
                    user_id=user.id,
                    pipeline_input=_copy_analysis_input(run_id=run_id),
                    filename="upload.mp4",
                    file=BytesIO(b"upload-bytes"),
                )

            failed_job = await store.jobs.get_job_by_run_id(run_id)
            assert failed_job is not None
            failed_job_id = failed_job.id

        async with session_factory() as session:
            store = create_store(session)
            persisted_job = await store.jobs.get_job(failed_job_id)

        assert persisted_job is not None
        assert persisted_job.status == JOB_STATUS_FAILED
        assert persisted_job.error_json is not None
        assert persisted_job.error_json["code"] == "pipeline_execution_failed"

    _run_async(scenario())


@pytest.fixture()
def integration_database_url() -> str:
    """Return a configured async database URL for pipeline integration tests."""

    database_url = os.getenv("APP_STORE_INTEGRATION_DATABASE_URL")

    if not database_url:
        pytest.skip(
            "Set APP_STORE_INTEGRATION_DATABASE_URL to run pipeline integration "
            "tests."
        )

    _upgrade_database(database_url)
    return database_url


@pytest.fixture()
def async_engine(integration_database_url: str) -> Iterator[AsyncEngine]:
    """Create and dispose the async engine used by integration tests."""

    engine = create_async_engine(integration_database_url)

    try:
        yield engine
    finally:
        _run_async(engine.dispose())


@pytest.fixture()
def session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return the session factory for real pipeline persistence tests."""

    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


class QueueFailure(RuntimeError):
    """Controlled queue failure used by integration tests."""


async def _create_user(store: AppStore) -> User:
    return await store.users.create_user(
        {
            "email": f"user-{uuid4().hex}@example.com",
            "password_hash": "hashed-password",
        }
    )


def _copy_analysis_input(*, run_id: str) -> CopyAnalysisPipelineInput:
    return CopyAnalysisPipelineInput(
        source_type="video",
        run_id=run_id,
        language="pt-BR",
        transcriber_provider="whisper_local",
        transcriber_model="small",
        llm_provider="openrouter",
        analysis_model="deepseek/deepseek-v4-flash",
        max_duration_seconds=300,
        output_formats=["json"],
    )


def _record_job_id(
    queued_job_ids: list[int],
) -> Callable[[int], Awaitable[None]]:
    async def handler(job_id: int) -> None:
        queued_job_ids.append(job_id)

    return handler


async def _failing_handler(job_id: int) -> None:
    raise QueueFailure(f"Failed to enqueue job {job_id}")


def _run_id() -> str:
    return f"run_{uuid4().hex}"


def _upgrade_database(database_url: str) -> None:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _run_async(coroutine: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coroutine)
