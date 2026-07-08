"""Factory helpers for application stores.

This module centralizes store construction. It does not create database engines,
open sessions, commit transactions, or decide which request owns a transaction.
Callers pass an active ``AsyncSession`` created by ``app.store.database``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.base import BillingStoreBase, JobStoreBase, UserStoreBase
from app.store.billing import BillingStore
from app.store.jobs import JobStore
from app.store.users import UserStore


@dataclass(frozen=True)
class AppStore:
    """Container for all domain stores sharing the same session."""

    jobs: JobStoreBase
    users: UserStoreBase
    billing: BillingStoreBase


def create_store(session: AsyncSession) -> AppStore:
    """Create all app stores for a single SQLAlchemy async session.

    The returned stores share the same session so the caller can compose
    multiple operations inside one external transaction:

    ``async with session.begin():``
      ``store = create_store(session)``
      ``await store.jobs.create_job(...)``
      ``await store.billing.set_stripe_customer(...)``
    """

    return AppStore(
        jobs=JobStore(session),
        users=UserStore(session),
        billing=BillingStore(session),
    )


__all__ = [
    "AppStore",
    "create_store",
]
