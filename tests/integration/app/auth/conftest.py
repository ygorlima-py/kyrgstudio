"""Database and service fixtures for authentication integration tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.store.models import AuthSession, User
from auth_helpers import (
    AuthIntegrationContext,
    build_auth_context,
    run_async,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"


def _upgrade_database(database_url: str) -> None:
    """Apply the production Alembic history to the integration database."""

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    previous_database_url = os.environ.get("APP_DATABASE_URL")
    os.environ["APP_DATABASE_URL"] = database_url

    try:
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("APP_DATABASE_URL", None)
        else:
            os.environ["APP_DATABASE_URL"] = previous_database_url


@pytest.fixture(scope="session")
def auth_database_url() -> str:
    """Return the explicitly configured disposable integration database."""

    database_url = os.getenv(
        "APP_AUTH_INTEGRATION_DATABASE_URL"
    ) or os.getenv("APP_STORE_INTEGRATION_DATABASE_URL")

    if not database_url:
        pytest.skip(
            "Set APP_AUTH_INTEGRATION_DATABASE_URL or "
            "APP_STORE_INTEGRATION_DATABASE_URL to run auth integration tests."
        )

    _upgrade_database(database_url)
    return database_url


@pytest.fixture(scope="session")
def auth_engine(auth_database_url: str) -> Iterator[AsyncEngine]:
    """Create and dispose the async integration database engine."""

    # Tests call async scenarios through separate event loops. NullPool avoids
    # reusing an asyncpg connection that belongs to a previous loop.
    engine = create_async_engine(
        auth_database_url,
        poolclass=pool.NullPool,
    )

    try:
        yield engine
    finally:
        run_async(engine.dispose())


@pytest.fixture(scope="session")
def auth_session_factory(
    auth_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return sessions configured like the application store."""

    return async_sessionmaker(
        bind=auth_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture(autouse=True)
def clean_auth_tables(
    auth_session_factory: async_sessionmaker[AsyncSession],
) -> Iterator[None]:
    """Isolate tests by clearing persisted auth state before and after each case."""

    async def clear() -> None:
        async with auth_session_factory.begin() as session:
            await session.execute(delete(AuthSession))
            await session.execute(delete(User))

    run_async(clear())
    yield
    run_async(clear())


@pytest.fixture()
def auth_context(
    auth_session_factory: async_sessionmaker[AsyncSession],
) -> AuthIntegrationContext:
    """Return real authentication services connected to the temporary store."""

    return build_auth_context(auth_session_factory)
