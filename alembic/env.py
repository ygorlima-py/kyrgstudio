"""Alembic environment for application store migrations.

This file connects Alembic to the SQLAlchemy models in ``app.store.models`` and
runs migrations through SQLAlchemy's async engine. The database URL is read from
``APP_DATABASE_URL`` or ``DATABASE_URL`` so secrets are not stored in
``alembic.ini``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app.store.models import Base  # noqa: E402


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_dotenv(PROJECT_ROOT / ".env")

target_metadata = Base.metadata


def _database_url() -> str:
    """Return the database URL used by Alembic migrations."""

    url = (
        os.getenv("APP_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )

    if url is None or url.strip() == "":
        raise RuntimeError(
            "Alembic database URL is missing. Set APP_DATABASE_URL or DATABASE_URL."
        )

    return url


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""

    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection) -> None:
    """Configure Alembic with a live sync connection wrapped by async engine."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _configuration(database_url: str) -> dict[str, str]:
    """Return Alembic engine configuration for a specific database URL."""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url
    return configuration


def _is_async_url(database_url: str) -> bool:
    """Return whether a SQLAlchemy URL uses an async driver."""

    driver = make_url(database_url).get_driver_name()
    return driver in {"aiosqlite", "asyncpg"}


async def run_async_migrations_online(database_url: str) -> None:
    """Run migrations using SQLAlchemy's async engine."""

    connectable = async_engine_from_config(
        _configuration(database_url),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations)

    await connectable.dispose()


def run_sync_migrations_online(database_url: str) -> None:
    """Run migrations using SQLAlchemy's synchronous engine."""

    connectable = engine_from_config(
        _configuration(database_url),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _run_migrations(connection)

    connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with the engine type required by the configured URL."""

    database_url = _database_url()

    if _is_async_url(database_url):
        asyncio.run(run_async_migrations_online(database_url))
        return

    run_sync_migrations_online(database_url)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
