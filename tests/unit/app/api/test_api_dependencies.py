"""Unit tests for API resource and service dependencies."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, BinaryIO, Callable, TypeVar, cast

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

import app.api.dependencies as api_dependencies
from app.errors import ProviderConfigError
from app.pipeline.service import PipelineService
from app.queue.base import QueueBase
from app.settings import AppSettings
from app.storage.base import StorageBase, StoredFile
from app.store.base import JobStoreBase
from app.store.database import SessionFactory


ResultT = TypeVar("ResultT")
ResourceGetter = Callable[[Request], object]


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings() -> AppSettings:
    """Return complete settings without reading the process environment."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-dependencies-storage"),
        sqlite_path=Path("/tmp/kyrg-api-dependencies.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-dependencies.sqlite",
        database_echo=False,
        database_pool_size=5,
        database_max_overflow=10,
        database_pool_pre_ping=True,
        openrouter_api_key=None,
        openai_api_key=None,
        gemini_api_key=None,
        default_llm_provider="openrouter",
        default_analysis_model="analysis-model",
        default_adaptation_model="adaptation-model",
        default_transcriber_provider="whisper_local",
        default_transcriber_model="small",
        max_duration_seconds=300,
        request_timeout_seconds=300,
        celery_broker_url="memory://",
        celery_queue_name="pipeline-test",
        celery_task_soft_time_limit_seconds=1800,
        celery_task_time_limit_seconds=1860,
    )


class _StorageStub(StorageBase):
    """Concrete storage sentinel accepted by runtime dependency checks."""

    def save_file(
        self,
        source_path: Path,
        destination_key: str,
    ) -> StoredFile:
        raise NotImplementedError

    def save_upload(
        self,
        file: BinaryIO,
        destination_key: str,
    ) -> StoredFile:
        raise NotImplementedError

    def download_file(self, key: str, destination_path: Path) -> Path:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def uri(self, key: str) -> str:
        raise NotImplementedError

    def delete_prefix(self, prefix: str) -> None:
        raise NotImplementedError


class _QueueStub(QueueBase):
    """Concrete queue sentinel accepted by runtime dependency checks."""

    async def enqueue(self, job_id: int) -> None:
        raise NotImplementedError


def _request(**resources: object) -> Request:
    """Create a request whose application state contains selected resources."""

    application = FastAPI()

    for resource_name, resource in resources.items():
        setattr(application.state, resource_name, resource)

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/v1/jobs",
        "raw_path": b"/v1/jobs",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("api.example.com", 443),
        "app": application,
    }
    return Request(scope)


def test_get_settings_returns_application_settings() -> None:
    """Return the exact settings instance installed by the lifespan."""

    settings = _settings()

    result = api_dependencies.get_settings(_request(settings=settings))

    assert result is settings


def test_get_session_factory_returns_application_factory() -> None:
    """Return the shared async session factory from application state."""

    session_factory = async_sessionmaker(expire_on_commit=False)

    result = api_dependencies.get_session_factory(
        _request(session_factory=session_factory)
    )

    assert result is session_factory


def test_get_storage_returns_application_storage() -> None:
    """Return the configured storage contract implementation."""

    storage = _StorageStub()

    result = api_dependencies.get_storage(_request(storage=storage))

    assert result is storage


def test_get_queue_returns_application_queue() -> None:
    """Return the configured queue contract implementation."""

    queue = _QueueStub()

    result = api_dependencies.get_queue(_request(queue=queue))

    assert result is queue


@pytest.mark.parametrize(
    ("resource_name", "getter"),
    [
        ("settings", api_dependencies.get_settings),
        ("session_factory", api_dependencies.get_session_factory),
        ("storage", api_dependencies.get_storage),
        ("queue", api_dependencies.get_queue),
    ],
)
@pytest.mark.parametrize("resource_state", ["missing", "invalid"])
def test_resource_dependencies_reject_missing_or_invalid_state(
    resource_name: str,
    getter: ResourceGetter,
    resource_state: str,
) -> None:
    """Reject absent resources and objects violating the expected contract."""

    resources = (
        {}
        if resource_state == "missing"
        else {resource_name: object()}
    )

    with pytest.raises(ProviderConfigError) as error_info:
        getter(_request(**resources))

    assert error_info.value.step == "configuring_api"
    assert error_info.value.details == {"resource": resource_name}


def test_get_session_yields_and_closes_read_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yield one request session and exit its scope after consumption."""

    session_factory = cast(SessionFactory, object())
    session = cast(AsyncSession, object())
    scope_events: list[tuple[str, object]] = []

    @asynccontextmanager
    async def session_scope(
        received_factory: SessionFactory,
    ) -> AsyncGenerator[AsyncSession, None]:
        scope_events.append(("opened", received_factory))
        try:
            yield session
        finally:
            scope_events.append(("closed", session))

    monkeypatch.setattr(
        api_dependencies,
        "async_session_scope",
        session_scope,
    )

    async def scenario() -> None:
        session_iterator = cast(
            AsyncGenerator[AsyncSession, None],
            api_dependencies.get_session(session_factory),
        )
        yielded_session = await anext(session_iterator)

        assert yielded_session is session
        assert scope_events == [("opened", session_factory)]

        await session_iterator.aclose()

    _run(scenario())

    assert scope_events == [
        ("opened", session_factory),
        ("closed", session),
    ]


def test_get_job_store_uses_request_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Construct the SQLAlchemy read store over the request-scoped session."""

    session = cast(AsyncSession, object())
    job_store = cast(JobStoreBase, object())
    received_sessions: list[AsyncSession] = []

    def create_job_store(received_session: AsyncSession) -> JobStoreBase:
        received_sessions.append(received_session)
        return job_store

    monkeypatch.setattr(
        api_dependencies,
        "SQLAlchemyJobStore",
        create_job_store,
    )

    result = api_dependencies.get_job_store(session)

    assert result is job_store
    assert received_sessions == [session]


def test_get_pipeline_service_uses_transactional_job_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the submission adapter that commits each pipeline checkpoint."""

    session_factory = cast(SessionFactory, object())
    storage = _StorageStub()
    queue = _QueueStub()
    transactional_store = object()
    received_factories: list[SessionFactory] = []

    def create_transactional_store(
        received_factory: SessionFactory,
    ) -> object:
        received_factories.append(received_factory)
        return transactional_store

    monkeypatch.setattr(
        api_dependencies,
        "PipelineJobStore",
        create_transactional_store,
    )

    service = api_dependencies.get_pipeline_service(
        session_factory,
        storage,
        queue,
    )

    assert isinstance(service, PipelineService)
    assert service.job_store is transactional_store
    assert received_factories == [session_factory]


def test_get_pipeline_service_reuses_storage_and_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject the lifespan-owned storage and queue without recreating them."""

    session_factory = cast(SessionFactory, object())
    storage = _StorageStub()
    queue = _QueueStub()

    monkeypatch.setattr(
        api_dependencies,
        "PipelineJobStore",
        lambda received_factory: object(),
    )

    service = api_dependencies.get_pipeline_service(
        session_factory,
        storage,
        queue,
    )

    assert service.storage is storage
    assert service.queue is queue
