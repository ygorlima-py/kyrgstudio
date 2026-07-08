"""Shared fixtures for app store integration tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from _helpers import run_async, upgrade_database


@pytest.fixture()
def empty_database_url(tmp_path: Path) -> str:
    """Return a sync SQLite URL for an empty temporary migration database."""

    return f"sqlite:///{tmp_path / 'app_store.db'}"


@pytest.fixture()
def migrated_database_url(empty_database_url: str) -> str:
    """Return a temporary database URL after applying Alembic migrations."""

    upgrade_database(empty_database_url)
    return empty_database_url


@pytest.fixture()
def async_store_database_url() -> str:
    """Return a disposable async database URL for store persistence tests."""

    database_url = os.getenv("APP_STORE_INTEGRATION_DATABASE_URL")

    if not database_url:
        pytest.skip(
            "Set APP_STORE_INTEGRATION_DATABASE_URL to run async store "
            "integration tests."
        )

    upgrade_database(database_url)
    return database_url


@pytest.fixture()
def async_engine(async_store_database_url: str) -> Iterator[AsyncEngine]:
    """Create and dispose an async engine for a migrated integration database."""

    engine = create_async_engine(async_store_database_url)

    try:
        yield engine
    finally:
        run_async(engine.dispose())


@pytest.fixture()
def session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return the session factory used by integration tests."""

    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
