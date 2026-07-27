"""Unit tests for API resource composition and lifecycle management."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from fastapi import FastAPI

import app.api.lifespan as lifespan_module
from app.errors import AuthConfigurationError
from app.queue.celery import CeleryTask
from app.settings import AppSettings
from app.store.database import SessionFactory


ResultT = TypeVar("ResultT")


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings() -> AppSettings:
    """Return complete, deterministic settings for lifecycle tests."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-lifespan-storage"),
        sqlite_path=Path("/tmp/kyrg-api-lifespan.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-lifespan.sqlite",
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
        auth_jwt_secret="a-secure-test-secret-with-32-bytes",
        auth_jwt_algorithm="HS256",
        auth_issuer="test-issuer",
        auth_audience="test-audience",
        auth_access_token_ttl_seconds=900,
        auth_refresh_token_ttl_seconds=3600,
        auth_allowed_clock_skew_seconds=15,
        google_client_ids=("client.apps.googleusercontent.com",),
    )


@dataclass(slots=True)
class _LifecycleFakes:
    """Sentinel resources and call history used by lifespan tests."""

    engine: object
    session_factory: object
    storage: object
    queue: object
    auth_service: object
    events: list[tuple[str, object]]
    disposed_engines: list[object]


def _install_lifecycle_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> _LifecycleFakes:
    fakes = _LifecycleFakes(
        engine=object(),
        session_factory=object(),
        storage=object(),
        queue=object(),
        auth_service=object(),
        events=[],
        disposed_engines=[],
    )

    def create_engine(settings: AppSettings) -> object:
        fakes.events.append(("create_engine", settings))
        return fakes.engine

    def create_session_factory(engine: object) -> object:
        fakes.events.append(("create_session_factory", engine))
        return fakes.session_factory

    def create_storage(settings: AppSettings) -> object:
        fakes.events.append(("create_storage", settings))
        return fakes.storage

    def create_queue() -> object:
        fakes.events.append(("create_queue", fakes.queue))
        return fakes.queue

    def create_auth_service(
        *,
        settings: AppSettings,
        session_factory: object,
    ) -> object:
        fakes.events.append(("create_auth_service", settings))
        fakes.events.append(("auth_session_factory", session_factory))
        return fakes.auth_service

    async def dispose_engine(engine: object) -> None:
        fakes.disposed_engines.append(engine)

    monkeypatch.setattr(
        lifespan_module,
        "create_async_engine_from_settings",
        create_engine,
    )
    monkeypatch.setattr(
        lifespan_module,
        "create_async_session_factory",
        create_session_factory,
    )
    monkeypatch.setattr(lifespan_module, "create_storage", create_storage)
    monkeypatch.setattr(lifespan_module, "_create_pipeline_queue", create_queue)
    monkeypatch.setattr(
        lifespan_module,
        "_create_auth_service",
        create_auth_service,
    )
    monkeypatch.setattr(
        lifespan_module,
        "dispose_async_engine",
        dispose_engine,
    )

    return fakes


def test_lifespan_reuses_preconfigured_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefer settings already validated during application construction."""

    settings = _settings()
    application = FastAPI()
    application.state.settings = settings
    fakes = _install_lifecycle_fakes(monkeypatch)

    def unexpected_settings_load() -> AppSettings:
        raise AssertionError("load_settings must not be called")

    monkeypatch.setattr(
        lifespan_module,
        "load_settings",
        unexpected_settings_load,
    )

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            pass

    _run(scenario())

    assert fakes.events[0] == ("create_engine", settings)
    assert application.state.settings is settings


def test_lifespan_rejects_invalid_preconfigured_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject arbitrary state objects before allocating infrastructure."""

    application = FastAPI()
    application.state.settings = object()
    engine_calls: list[AppSettings] = []

    monkeypatch.setattr(
        lifespan_module,
        "create_async_engine_from_settings",
        engine_calls.append,
    )

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            pass

    with pytest.raises(
        AuthConfigurationError,
        match="invalid type",
    ):
        _run(scenario())

    assert engine_calls == []


def test_lifespan_creates_session_factory_storage_queue_and_auth_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compose each process-scoped dependency exactly once."""

    settings = _settings()
    application = FastAPI()
    application.state.settings = settings
    fakes = _install_lifecycle_fakes(monkeypatch)

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            pass

    _run(scenario())

    assert fakes.events == [
        ("create_engine", settings),
        ("create_session_factory", fakes.engine),
        ("create_storage", settings),
        ("create_queue", fakes.queue),
        ("create_auth_service", settings),
        ("auth_session_factory", fakes.session_factory),
    ]


def test_lifespan_exposes_resources_through_application_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose composed dependencies to request-level API dependencies."""

    settings = _settings()
    application = FastAPI()
    application.state.settings = settings
    fakes = _install_lifecycle_fakes(monkeypatch)

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            assert application.state.settings is settings
            assert application.state.session_factory is fakes.session_factory
            assert application.state.storage is fakes.storage
            assert application.state.queue is fakes.queue
            assert application.state.auth_service is fakes.auth_service

    _run(scenario())


def test_lifespan_disposes_engine_on_normal_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release the API-owned engine after a normal lifespan shutdown."""

    application = FastAPI()
    application.state.settings = _settings()
    fakes = _install_lifecycle_fakes(monkeypatch)

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            assert fakes.disposed_engines == []

    _run(scenario())

    assert fakes.disposed_engines == [fakes.engine]


@pytest.mark.parametrize("failure_stage", ["startup", "application"])
def test_lifespan_disposes_engine_when_startup_or_application_fails(
    failure_stage: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release the engine after startup and application-level failures."""

    application = FastAPI()
    application.state.settings = _settings()
    fakes = _install_lifecycle_fakes(monkeypatch)
    expected_error = RuntimeError(f"{failure_stage} failed")

    if failure_stage == "startup":

        def failing_storage_factory(settings: AppSettings) -> object:
            del settings
            raise expected_error

        monkeypatch.setattr(
            lifespan_module,
            "create_storage",
            failing_storage_factory,
        )

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            if failure_stage == "application":
                raise expected_error

    with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
        _run(scenario())

    assert fakes.disposed_engines == [fakes.engine]


def test_lifespan_does_not_execute_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build the queue without enqueueing or executing its Celery task."""

    from app.worker import tasks as worker_tasks

    settings = _settings()
    application = FastAPI()
    application.state.settings = settings
    create_pipeline_queue = lifespan_module._create_pipeline_queue
    fakes = _install_lifecycle_fakes(monkeypatch)
    task_calls: list[int] = []

    class TaskProbe:
        def delay(self, job_id: int) -> object:
            task_calls.append(job_id)
            return object()

    task = TaskProbe()
    queue = lifespan_module.CeleryQueue(task)

    monkeypatch.setattr(worker_tasks, "run_pipeline_job", task)
    monkeypatch.setattr(
        lifespan_module,
        "_create_pipeline_queue",
        create_pipeline_queue,
    )
    monkeypatch.setattr(
        lifespan_module,
        "CeleryQueue",
        lambda received_task: queue
        if received_task is task
        else pytest.fail("Unexpected Celery task"),
    )

    async def scenario() -> None:
        async with lifespan_module.api_lifespan(application):
            assert application.state.queue is queue

    _run(scenario())

    assert task_calls == []
    assert fakes.disposed_engines == [fakes.engine]


def test_create_auth_service_uses_auth_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass validated auth configuration and composed dependencies exactly."""

    settings = _settings()
    session_factory = cast(SessionFactory, object())
    auth_store = object()
    password_hasher = object()
    access_tokens = object()
    refresh_tokens = object()
    google_verifier = object()
    auth_service = object()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        lifespan_module,
        "AuthStore",
        lambda received_factory: (
            captured.update(auth_store_factory=received_factory) or auth_store
        ),
    )
    monkeypatch.setattr(
        lifespan_module,
        "Argon2PasswordHasher",
        lambda: password_hasher,
    )

    def create_access_tokens(**kwargs: Any) -> object:
        captured["access_token_settings"] = kwargs
        return access_tokens

    monkeypatch.setattr(
        lifespan_module,
        "AccessTokenService",
        create_access_tokens,
    )
    monkeypatch.setattr(
        lifespan_module,
        "RefreshTokenGenerator",
        lambda: refresh_tokens,
    )

    def create_google_verifier(**kwargs: Any) -> object:
        captured["google_settings"] = kwargs
        return google_verifier

    monkeypatch.setattr(
        lifespan_module,
        "GoogleTokenVerifier",
        create_google_verifier,
    )

    def create_service(**kwargs: Any) -> object:
        captured["auth_service_dependencies"] = kwargs
        return auth_service

    monkeypatch.setattr(lifespan_module, "AuthService", create_service)

    result = lifespan_module._create_auth_service(
        settings=settings,
        session_factory=session_factory,
    )

    assert result is auth_service
    assert captured["auth_store_factory"] is session_factory
    assert captured["access_token_settings"] == {
        "secret": settings.auth_jwt_secret,
        "issuer": settings.auth_issuer,
        "audience": settings.auth_audience,
        "algorithm": settings.auth_jwt_algorithm,
        "ttl_seconds": settings.auth_access_token_ttl_seconds,
        "allowed_clock_skew_seconds": (
            settings.auth_allowed_clock_skew_seconds
        ),
    }
    assert captured["google_settings"] == {
        "client_ids": settings.google_client_ids,
        "allowed_clock_skew_seconds": (
            settings.auth_allowed_clock_skew_seconds
        ),
    }
    assert captured["auth_service_dependencies"] == {
        "auth_store": auth_store,
        "password_hasher": password_hasher,
        "access_token_service": access_tokens,
        "refresh_token_generator": refresh_tokens,
        "google_token_verifier": google_verifier,
        "refresh_token_ttl_seconds": (
            settings.auth_refresh_token_ttl_seconds
        ),
    }


def test_create_auth_service_rejects_missing_jwt_secret() -> None:
    """Fail with a controlled auth error before constructing dependencies."""

    settings = replace(_settings(), auth_jwt_secret=None)

    with pytest.raises(
        AuthConfigurationError,
        match="JWT configuration is invalid",
    ) as error_info:
        lifespan_module._create_auth_service(
            settings=settings,
            session_factory=cast(SessionFactory, object()),
        )

    assert isinstance(error_info.value.__cause__, ValueError)


def test_create_auth_service_allows_google_authentication_to_be_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start password authentication without configured Google client IDs."""

    settings = replace(_settings(), google_client_ids=())
    captured_dependencies: dict[str, Any] = {}
    auth_service = object()

    def reject_google_verifier_creation(**kwargs: Any) -> object:
        raise AssertionError(
            "GoogleTokenVerifier must not be created without client IDs."
        )

    def create_auth_service(**kwargs: Any) -> object:
        captured_dependencies.update(kwargs)
        return auth_service

    monkeypatch.setattr(
        lifespan_module,
        "GoogleTokenVerifier",
        reject_google_verifier_creation,
    )
    monkeypatch.setattr(
        lifespan_module,
        "AuthService",
        create_auth_service,
    )

    result = lifespan_module._create_auth_service(
        settings=settings,
        session_factory=cast(SessionFactory, object()),
    )

    assert result is auth_service
    assert captured_dependencies["google_token_verifier"] is None


def test_create_pipeline_queue_wraps_public_celery_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject the registered public task into the Celery queue adapter."""

    from app.worker.tasks import run_pipeline_job

    queue = object()
    received_tasks: list[CeleryTask] = []

    def create_queue(task: CeleryTask) -> object:
        received_tasks.append(task)
        return queue

    monkeypatch.setattr(lifespan_module, "CeleryQueue", create_queue)

    result = lifespan_module._create_pipeline_queue()

    assert result is queue
    assert received_tasks == [cast(CeleryTask, run_pipeline_job)]
