"""Async database infrastructure for the application store.

This module owns SQLAlchemy engine and session creation. Store/repository
classes should receive an active ``AsyncSession`` from this layer instead of
creating engines or committing transactions by themselves.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.errors import StoreError


DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10

_ALLOWED_ASYNC_DRIVERS = {
    ("postgresql", "asyncpg"),
    ("sqlite", "aiosqlite"),
}


@dataclass(frozen=True)
class DatabaseConfig:
    """Validated database settings used to build an async SQLAlchemy engine."""

    url: str
    echo: bool = False
    pool_size: int = DEFAULT_POOL_SIZE
    max_overflow: int = DEFAULT_MAX_OVERFLOW
    pool_pre_ping: bool = True

    @classmethod
    def from_settings(cls, settings: object) -> "DatabaseConfig":
        """Create database config from an application settings object."""

        return cls(
            url=_required_setting(settings, "database_url"),
            echo=_bool_setting(settings, "database_echo", default=False),
            pool_size=_int_setting(
                settings,
                "database_pool_size",
                default=DEFAULT_POOL_SIZE,
                minimum=1,
            ),
            max_overflow=_int_setting(
                settings,
                "database_max_overflow",
                default=DEFAULT_MAX_OVERFLOW,
                minimum=0,
            ),
            pool_pre_ping=_bool_setting(
                settings,
                "database_pool_pre_ping",
                default=True,
            ),
        )

    @property
    def is_sqlite(self) -> bool:
        """Return whether the configured database is SQLite."""

        url = make_url(self.url)
        return url.get_backend_name() == "sqlite"


SessionFactory = async_sessionmaker[AsyncSession]


def create_async_engine_from_settings(settings: object) -> AsyncEngine:
    """Create an async SQLAlchemy engine from application settings."""

    return create_async_engine_from_config(DatabaseConfig.from_settings(settings))


def create_async_engine_from_config(config: DatabaseConfig) -> AsyncEngine:
    """Create an async SQLAlchemy engine from validated database config."""

    _validate_async_database_url(config.url)

    engine_kwargs: dict[str, Any] = {
        "echo": config.echo,
    }

    # SQLite's async driver does not accept the same QueuePool options as
    # Postgres. Keep pool tuning scoped to production-style backends.
    if not config.is_sqlite:
        engine_kwargs["pool_pre_ping"] = config.pool_pre_ping
        engine_kwargs["pool_size"] = config.pool_size
        engine_kwargs["max_overflow"] = config.max_overflow

    try:
        return create_async_engine(config.url, **engine_kwargs)
    except SQLAlchemyError as error:
        raise StoreError(
            technical_message=f"Failed to create async database engine: {error}",
            details={"operation": "create_async_engine"},
        ) from error


def create_async_session_factory(engine: AsyncEngine) -> SessionFactory:
    """Create the session factory used by stores and service layers."""

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@asynccontextmanager
async def async_session_scope(
    session_factory: SessionFactory,
) -> AsyncIterator[AsyncSession]:
    """Open and close an ``AsyncSession`` without committing automatically."""

    try:
        async with session_factory() as session:
            yield session
    except SQLAlchemyError as error:
        raise StoreError(
            technical_message=f"Database session failed: {error}",
            details={"operation": "session_scope"},
        ) from error


@asynccontextmanager
async def async_transaction_scope(
    session_factory: SessionFactory,
) -> AsyncIterator[AsyncSession]:
    """Open an ``AsyncSession`` and wrap the block in one transaction."""

    try:
        async with session_factory() as session:
            async with session.begin():
                yield session
    except SQLAlchemyError as error:
        raise StoreError(
            technical_message=f"Database transaction failed: {error}",
            details={"operation": "transaction_scope"},
        ) from error


@asynccontextmanager
async def async_savepoint_scope(
    session: AsyncSession,
) -> AsyncIterator[AsyncSession]:
    """Create a nested transaction/savepoint inside an active session.

    SQLAlchemy exceptions are intentionally not wrapped here. Domain stores need
    to catch specific errors such as ``IntegrityError`` to implement safe
    idempotency without aborting the outer transaction.
    """

    async with session.begin_nested():
        yield session


async def dispose_async_engine(engine: AsyncEngine) -> None:
    """Dispose database connections held by an async engine."""

    try:
        await engine.dispose()
    except SQLAlchemyError as error:
        raise StoreError(
            technical_message=f"Failed to dispose database engine: {error}",
            details={"operation": "dispose_async_engine"},
        ) from error


def _validate_async_database_url(url: str) -> None:
    try:
        parsed_url = make_url(url)
    except SQLAlchemyError as error:
        raise StoreError(
            technical_message=f"Invalid database URL: {error}",
            details={"setting": "database_url"},
        ) from error

    backend = parsed_url.get_backend_name()
    driver = parsed_url.get_driver_name()

    if (backend, driver) not in _ALLOWED_ASYNC_DRIVERS:
        raise StoreError(
            technical_message=(
                "DATABASE_URL must use an async SQLAlchemy driver."
            ),
            details={
                "backend": backend,
                "driver": driver,
                "allowed": sorted(
                    f"{allowed_backend}+{allowed_driver}"
                    for allowed_backend, allowed_driver in _ALLOWED_ASYNC_DRIVERS
                ),
            },
        )


def _required_setting(settings: object, name: str) -> str:
    value = getattr(settings, name, None)

    if value is None or str(value).strip() == "":
        raise StoreError(
            technical_message=f"Required database setting is missing: {name}",
            details={"missing_setting": name},
        )

    return str(value)


def _bool_setting(settings: object, name: str, *, default: bool) -> bool:
    value = getattr(settings, name, default)

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise StoreError(
        technical_message=f"Invalid boolean database setting: {name}",
        details={"setting": name, "value": value},
    )


def _int_setting(
    settings: object,
    name: str,
    *,
    default: int,
    minimum: int,
) -> int:
    value = getattr(settings, name, default)

    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as error:
        raise StoreError(
            technical_message=f"Invalid integer database setting: {name}",
            details={"setting": name, "value": value},
        ) from error

    if parsed_value < minimum:
        raise StoreError(
            technical_message=f"Database setting is below minimum: {name}",
            details={
                "setting": name,
                "value": parsed_value,
                "minimum": minimum,
            },
        )

    return parsed_value


__all__ = [
    "DatabaseConfig",
    "SessionFactory",
    "async_savepoint_scope",
    "async_session_scope",
    "async_transaction_scope",
    "create_async_engine_from_config",
    "create_async_engine_from_settings",
    "create_async_session_factory",
    "dispose_async_engine",
]
