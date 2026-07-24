"""Database fixtures for HTTP API integration tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine, Iterator
from pathlib import Path
from typing import Any, TypeVar

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


ResultT = TypeVar("ResultT")
PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"


def run_async(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Execute one asynchronous integration scenario."""

    return asyncio.run(coroutine)


def _upgrade_database(database_url: str) -> None:
    """Apply the production migration history to a temporary database."""

    configuration = Config(str(ALEMBIC_INI_PATH))
    configuration.set_main_option(
        "script_location",
        str(ALEMBIC_SCRIPT_LOCATION),
    )
    configuration.set_main_option("sqlalchemy.url", database_url)
    previous_database_url = os.environ.get("APP_DATABASE_URL")
    os.environ["APP_DATABASE_URL"] = database_url

    try:
        command.upgrade(configuration, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("APP_DATABASE_URL", None)
        else:
            os.environ["APP_DATABASE_URL"] = previous_database_url


@pytest.fixture(scope="session")
def api_database_url() -> str:
    """Return and migrate an explicitly configured disposable database."""

    database_url = os.getenv(
        "APP_API_INTEGRATION_DATABASE_URL"
    ) or os.getenv("APP_STORE_INTEGRATION_DATABASE_URL")

    if not database_url:
        pytest.skip(
            "Set APP_API_INTEGRATION_DATABASE_URL or "
            "APP_STORE_INTEGRATION_DATABASE_URL to run API integration tests."
        )

    _upgrade_database(database_url)
    return database_url


@pytest.fixture(scope="session")
def api_engine(api_database_url: str) -> Iterator[AsyncEngine]:
    """Own the async engine shared by API integration tests."""

    engine = create_async_engine(api_database_url)

    try:
        yield engine
    finally:
        run_async(engine.dispose())


@pytest.fixture(scope="session")
def api_session_factory(
    api_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return sessions configured like the application store."""

    return async_sessionmaker(
        bind=api_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
