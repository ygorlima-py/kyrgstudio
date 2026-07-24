"""Local helpers for app store integration tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"

T = TypeVar("T")


def run_async(awaitable: Any) -> Any:
    """Run async integration helpers from synchronous pytest tests."""

    return asyncio.run(awaitable)


def make_alembic_config(database_url: str) -> Config:
    """Build an Alembic config pointed at a temporary test database."""

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(database_url: str) -> None:
    """Apply all Alembic migrations to a temporary test database."""

    previous_database_url = os.environ.get("APP_DATABASE_URL")
    os.environ["APP_DATABASE_URL"] = database_url

    try:
        command.upgrade(make_alembic_config(database_url), "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("APP_DATABASE_URL", None)
        else:
            os.environ["APP_DATABASE_URL"] = previous_database_url


def inspect_database(
    database_url: str,
    callback: Callable[[Any], T],
) -> T:
    """Run a SQLAlchemy inspection callback against a sync engine."""

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            return callback(connection)
    finally:
        engine.dispose()
