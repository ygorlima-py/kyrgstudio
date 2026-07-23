"""Unit tests for FastAPI application composition."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import textwrap
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, TypeVar

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

import app.api.main as main_module
from app.api.middleware import RequestIdMiddleware
from app.errors import AppError
from app.settings import AppSettings


ResultT = TypeVar("ResultT")


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings(
    *,
    cors_origins: tuple[str, ...] = (),
) -> AppSettings:
    """Return complete settings without reading environment variables."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-main-storage"),
        sqlite_path=Path("/tmp/kyrg-api-main.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-main.sqlite",
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
        api_cors_origins=cors_origins,
    )


def _middleware_options(
    application: FastAPI,
    middleware_type: type[object],
) -> dict[str, Any]:
    """Return options for exactly one configured middleware class."""

    matching_middleware = [
        middleware
        for middleware in application.user_middleware
        if middleware.cls is middleware_type
    ]

    assert len(matching_middleware) == 1
    return matching_middleware[0].kwargs


def test_create_app_uses_explicit_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use injected settings without reading the process environment."""

    settings = _settings()

    def unexpected_settings_load() -> AppSettings:
        raise AssertionError("load_settings must not be called")

    monkeypatch.setattr(
        main_module,
        "load_settings",
        unexpected_settings_load,
    )

    application = main_module.create_app(settings)

    assert application.state.settings is settings


def test_create_app_loads_settings_once_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve environment configuration exactly once per application."""

    settings = _settings()
    load_calls = 0

    def load_settings() -> AppSettings:
        nonlocal load_calls
        load_calls += 1
        return settings

    monkeypatch.setattr(main_module, "load_settings", load_settings)

    application = main_module.create_app()

    assert load_calls == 1
    assert application.state.settings is settings


def test_create_app_configures_api_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute the configured API lifespan around application operation."""

    lifecycle_events: list[tuple[str, FastAPI]] = []

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        lifecycle_events.append(("startup", application))
        try:
            yield
        finally:
            lifecycle_events.append(("shutdown", application))

    monkeypatch.setattr(main_module, "api_lifespan", lifespan)
    application = main_module.create_app(_settings())

    async def scenario() -> None:
        async with application.router.lifespan_context(application):
            assert lifecycle_events == [("startup", application)]

    _run(scenario())

    assert lifecycle_events == [
        ("startup", application),
        ("shutdown", application),
    ]


def test_create_app_stores_resolved_settings() -> None:
    """Expose the same resolved settings to lifespan and dependencies."""

    settings = _settings()

    application = main_module.create_app(settings)

    assert application.state.settings is settings


def test_create_app_configures_explicit_cors_origins() -> None:
    """Allow credentials only for the configured browser origins."""

    origins = (
        "https://studio.example.com",
        "https://admin.example.com",
    )

    application = main_module.create_app(
        _settings(cors_origins=origins)
    )
    options = _middleware_options(application, CORSMiddleware)

    assert options["allow_origins"] == list(origins)
    assert options["allow_credentials"] is True
    assert options["allow_methods"] == ["GET", "POST", "OPTIONS"]
    assert "Authorization" in options["allow_headers"]
    assert "X-CSRF-Token" in options["allow_headers"]


def test_create_app_does_not_enable_wildcard_cors() -> None:
    """Reject wildcard browser access instead of combining it with cookies."""

    with pytest.raises(ValueError, match="wildcard is not allowed"):
        main_module.create_app(_settings(cors_origins=("*",)))


def test_create_app_installs_request_id_middleware() -> None:
    """Install exactly one request-correlation middleware."""

    application = main_module.create_app(_settings())

    options = _middleware_options(application, RequestIdMiddleware)

    assert options == {}


def test_create_app_installs_exception_handlers() -> None:
    """Install controlled, validation, and unexpected error boundaries."""

    application = main_module.create_app(_settings())

    assert AppError in application.exception_handlers
    assert RequestValidationError in application.exception_handlers
    assert Exception in application.exception_handlers


def test_create_app_registers_health_auth_and_jobs_routers() -> None:
    """Expose every planned API area through the generated route contract."""

    application = main_module.create_app(_settings())

    paths = set(application.openapi()["paths"])

    assert "/health" in paths
    assert "/v1/auth/register" in paths
    assert "/v1/auth/login" in paths
    assert "/v1/jobs" in paths
    assert "/v1/jobs/{job_id}" in paths
    assert "/v1/jobs/{job_id}/result" in paths


def test_importing_main_does_not_connect_to_infrastructure() -> None:
    """Build the module-level ASGI app without allocating runtime resources."""

    import_script = textwrap.dedent(
        """
        import importlib

        lifespan_module = importlib.import_module("app.api.lifespan")

        def fail_if_called(*args, **kwargs):
            raise AssertionError("infrastructure was initialized during import")

        lifespan_module.create_async_engine_from_settings = fail_if_called
        lifespan_module.create_async_session_factory = fail_if_called
        lifespan_module.create_storage = fail_if_called
        lifespan_module._create_pipeline_queue = fail_if_called
        lifespan_module._create_auth_service = fail_if_called

        main_module = importlib.import_module("app.api.main")
        assert main_module.app.state.settings is not None
        """
    )

    completed_process = subprocess.run(
        [sys.executable, "-c", import_script],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed_process.returncode == 0, completed_process.stderr


def test_module_app_is_created_by_create_app() -> None:
    """Expose one composed FastAPI instance as the module-level ASGI app."""

    application = main_module.app

    assert isinstance(application, FastAPI)
    assert isinstance(application.state.settings, AppSettings)
    assert "/health" in application.openapi()["paths"]
    assert any(
        middleware.cls is RequestIdMiddleware
        for middleware in application.user_middleware
    )
