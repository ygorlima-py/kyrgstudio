"""Shared fixtures for worker integration tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"


@pytest.fixture()
def async_worker_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Return a configured async database URL for worker integration tests."""

    database_url = (
        os.getenv("APP_WORKER_INTEGRATION_DATABASE_URL")
        or os.getenv("APP_STORE_INTEGRATION_DATABASE_URL")
    )

    if not database_url:
        pytest.skip(
            "Set APP_WORKER_INTEGRATION_DATABASE_URL or "
            "APP_STORE_INTEGRATION_DATABASE_URL to run worker database "
            "integration tests."
        )

    # Alembic gives APP_DATABASE_URL priority over its configured URL.
    monkeypatch.setenv("APP_DATABASE_URL", database_url)

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    return database_url


@pytest.fixture()
def async_engine(async_worker_database_url: str) -> Iterator[AsyncEngine]:
    """Create and dispose the async engine for a migrated worker database."""

    engine = create_async_engine(async_worker_database_url)

    try:
        yield engine
    finally:
        asyncio.run(engine.dispose())


@pytest.fixture()
def session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return the session factory shared by one integration test."""

    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
