"""Unit tests for app store factory wiring.

The factory must wire concrete stores around an existing session. It must not
open database connections, create engines, or own transaction boundaries.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.store.base import BillingStoreBase, JobStoreBase, UserStoreBase
from app.store.billing import SQLAlchemyBillingStore
from app.store.factory import AppStore, create_store
from app.store.jobs import SQLAlchemyJobStore
from app.store.users import SQLAlchemyUserStore


def _fake_session() -> AsyncSession:
    """Return a typed placeholder session without opening a database."""

    return cast(AsyncSession, object())


def test_create_store_returns_app_store() -> None:
    """create_store should return the aggregate AppStore container."""

    store = create_store(_fake_session())

    assert isinstance(store, AppStore)


def test_create_store_uses_same_session_for_all_stores() -> None:
    """Every concrete store should share the exact same session object."""

    session = _fake_session()
    store = create_store(session)

    assert isinstance(store.jobs, SQLAlchemyJobStore)
    assert isinstance(store.users, SQLAlchemyUserStore)
    assert isinstance(store.billing, SQLAlchemyBillingStore)
    assert store.jobs.session is session
    assert store.users.session is session
    assert store.billing.session is session


def test_create_store_returns_contract_typed_stores() -> None:
    """Factory output should expose stores through their stable contracts."""

    store = create_store(_fake_session())

    assert isinstance(store.jobs, JobStoreBase)
    assert isinstance(store.users, UserStoreBase)
    assert isinstance(store.billing, BillingStoreBase)


def test_app_store_is_frozen() -> None:
    """AppStore should be immutable after construction."""

    store = create_store(_fake_session())

    with pytest.raises(FrozenInstanceError):
        setattr(store, "jobs", store.jobs)
