"""Unit tests for app store abstract contracts.

These tests protect the public persistence contract used by API, worker,
pipeline, and service layers. They intentionally do not require a database.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.base import BillingStoreBase, JobStoreBase, UserStoreBase
from app.store.billing import SQLAlchemyBillingStore
from app.store.jobs import SQLAlchemyJobStore
from app.store.users import SQLAlchemyUserStore


def _abstract_methods(cls: type[object]) -> set[str]:
    """Return abstract method names declared by an ABC."""

    return set(getattr(cls, "__abstractmethods__", set()))


def test_job_store_base_declares_required_methods() -> None:
    """JobStoreBase should expose the full job persistence contract."""

    assert {
        "create_job",
        "mark_uploaded",
        "mark_running",
        "mark_step_completed",
        "mark_completed",
        "mark_failed",
        "get_job",
        "get_job_by_run_id",
        "list_user_jobs",
    } <= _abstract_methods(JobStoreBase)


def test_user_store_base_declares_required_methods() -> None:
    """UserStoreBase should expose the user lookup and creation contract."""

    assert {
        "create_user",
        "get_user",
        "get_user_by_email",
        "get_user_by_google_sub",
    } <= _abstract_methods(UserStoreBase)


def test_billing_store_base_declares_required_methods() -> None:
    """BillingStoreBase should expose customer, subscription, and event methods."""

    assert {
        "set_stripe_customer",
        "upsert_subscription",
        "record_billing_event",
        "get_subscription_by_user_id",
    } <= _abstract_methods(BillingStoreBase)


def test_concrete_stores_implement_abstract_contracts() -> None:
    """Concrete stores should be instantiable when given an active session."""

    session = cast(AsyncSession, object())

    job_store = SQLAlchemyJobStore(session)
    user_store = SQLAlchemyUserStore(session)
    billing_store = SQLAlchemyBillingStore(session)

    assert isinstance(job_store, JobStoreBase)
    assert isinstance(user_store, UserStoreBase)
    assert isinstance(billing_store, BillingStoreBase)
    assert job_store.session is session
    assert user_store.session is session
    assert billing_store.session is session
