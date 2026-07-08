"""Unit tests for app store database infrastructure.

These tests validate configuration parsing and SQLAlchemy factory wiring
without opening a real database connection. Integration tests own real engine,
transaction, and migration behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import app.store.database as database
from app.errors import StoreError
from app.store.database import DatabaseConfig


def test_database_config_from_settings_reads_expected_fields() -> None:
    """DatabaseConfig should map supported app settings into typed values."""

    settings = SimpleNamespace(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/kyrg",
        database_echo="true",
        database_pool_size="8",
        database_max_overflow="4",
        database_pool_pre_ping="false",
    )

    config = DatabaseConfig.from_settings(settings)

    assert config.url == settings.database_url
    assert config.echo is True
    assert config.pool_size == 8
    assert config.max_overflow == 4
    assert config.pool_pre_ping is False


def test_database_config_rejects_missing_database_url() -> None:
    """Missing database_url should fail before engine creation."""

    settings = SimpleNamespace(database_url="")

    with pytest.raises(StoreError) as error:
        DatabaseConfig.from_settings(settings)

    assert error.value.details == {"missing_setting": "database_url"}


def test_validate_async_database_url_accepts_postgresql_asyncpg() -> None:
    """Postgres URLs must use the asyncpg SQLAlchemy async driver."""

    database._validate_async_database_url(
        "postgresql+asyncpg://user:pass@localhost:5432/kyrg"
    )


def test_validate_async_database_url_accepts_sqlite_aiosqlite() -> None:
    """SQLite URLs must use the aiosqlite SQLAlchemy async driver."""

    database._validate_async_database_url("sqlite+aiosqlite:///./app.db")


def test_validate_async_database_url_rejects_sync_postgres_driver() -> None:
    """Synchronous Postgres URLs should be rejected for the async app store."""

    with pytest.raises(StoreError) as error:
        database._validate_async_database_url(
            "postgresql://user:pass@localhost:5432/kyrg"
        )

    assert error.value.details["backend"] == "postgresql"
    assert error.value.details["driver"] == "psycopg2"


def test_validate_async_database_url_rejects_sync_sqlite_driver() -> None:
    """Synchronous SQLite URLs should be rejected for the async app store."""

    with pytest.raises(StoreError) as error:
        database._validate_async_database_url("sqlite:///./app.db")

    assert error.value.details["backend"] == "sqlite"
    assert error.value.details["driver"] == "pysqlite"


def test_create_async_engine_from_config_uses_sqlite_safe_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite engines should not receive Postgres QueuePool tuning kwargs."""

    captured: dict[str, Any] = {}
    sentinel_engine = cast(AsyncEngine, object())

    def fake_create_async_engine(url: str, **kwargs: Any) -> AsyncEngine:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel_engine

    monkeypatch.setattr(
        database,
        "create_async_engine",
        fake_create_async_engine,
    )

    config = DatabaseConfig(
        url="sqlite+aiosqlite:///./app.db",
        echo=True,
        pool_size=9,
        max_overflow=3,
        pool_pre_ping=False,
    )

    engine = database.create_async_engine_from_config(config)

    assert engine is sentinel_engine
    assert captured == {
        "url": config.url,
        "kwargs": {"echo": True},
    }


def test_create_async_engine_from_config_uses_postgres_pool_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Postgres engines should receive configured pool behavior."""

    captured: dict[str, Any] = {}
    sentinel_engine = cast(AsyncEngine, object())

    def fake_create_async_engine(url: str, **kwargs: Any) -> AsyncEngine:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel_engine

    monkeypatch.setattr(
        database,
        "create_async_engine",
        fake_create_async_engine,
    )

    config = DatabaseConfig(
        url="postgresql+asyncpg://user:pass@localhost:5432/kyrg",
        echo=True,
        pool_size=12,
        max_overflow=6,
        pool_pre_ping=False,
    )

    engine = database.create_async_engine_from_config(config)

    assert engine is sentinel_engine
    assert captured == {
        "url": config.url,
        "kwargs": {
            "echo": True,
            "pool_pre_ping": False,
            "pool_size": 12,
            "max_overflow": 6,
        },
    }


def test_create_async_session_factory_uses_expire_on_commit_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session factories should keep ORM objects usable after commits."""

    captured: dict[str, Any] = {}
    sentinel_factory = object()
    engine = cast(AsyncEngine, object())

    def fake_async_sessionmaker(**kwargs: Any) -> object:
        captured.update(kwargs)
        return sentinel_factory

    monkeypatch.setattr(database, "async_sessionmaker", fake_async_sessionmaker)

    factory = database.create_async_session_factory(engine)

    assert factory is sentinel_factory
    assert captured == {
        "bind": engine,
        "class_": AsyncSession,
        "expire_on_commit": False,
        "autoflush": False,
    }
