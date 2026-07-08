"""Integration tests for app store persistence behavior."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import UserStoreError
from app.store.billing import SQLAlchemyBillingStore
from app.store.database import async_savepoint_scope
from app.store.jobs import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_UPLOADED,
    SQLAlchemyJobStore,
)
from app.store.models import BillingCustomer, BillingEvent, Subscription, User
from app.store.users import SQLAlchemyUserStore
from _helpers import run_async


def test_creating_a_user_and_reading_it_back(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A user written through the store should be readable from the database."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            store = SQLAlchemyUserStore(session)
            user = await store.create_user(
                {
                    "email": "USER@EXAMPLE.COM",
                    "password_hash": "hashed-password",
                }
            )
            assert user.id is not None

        async with session_factory() as session:
            store = SQLAlchemyUserStore(session)
            persisted_user = await store.get_user_by_email("user@example.com")

        assert persisted_user is not None
        assert persisted_user.email == "user@example.com"

    run_async(scenario())


def test_enforcing_unique_email(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The database should reject duplicate user emails."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            store = SQLAlchemyUserStore(session)
            await store.create_user(
                {
                    "email": "user@example.com",
                    "password_hash": "hashed-password",
                }
            )

            try:
                await store.create_user(
                    {
                        "email": "user@example.com",
                        "password_hash": "other-hash",
                    }
                )
            except UserStoreError as error:
                assert error.details["operation"] == "create_user"
                assert error.details["error_type"] == "IntegrityError"
            else:
                raise AssertionError("Duplicate email should fail")

    run_async(scenario())


def test_enforcing_unique_billing_customers_user_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A user should not have two billing customer rows."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            session.add_all(
                [
                    BillingCustomer(user_id=1, stripe_customer_id="cus_1"),
                    BillingCustomer(user_id=1, stripe_customer_id="cus_2"),
                ]
            )

            try:
                await session.flush()
            except IntegrityError:
                return

            raise AssertionError("Duplicate billing customer user_id should fail")

    run_async(scenario())


def test_enforcing_unique_billing_customers_stripe_customer_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A Stripe customer id should not be linked to two users."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            session.add_all(
                [
                    BillingCustomer(user_id=1, stripe_customer_id="cus_shared"),
                    BillingCustomer(user_id=2, stripe_customer_id="cus_shared"),
                ]
            )

            try:
                await session.flush()
            except IntegrityError:
                return

            raise AssertionError("Duplicate Stripe customer id should fail")

    run_async(scenario())


def test_allowing_multiple_subscriptions_for_same_stripe_customer_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Subscription history should allow multiple rows per customer id."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            session.add_all(
                [
                    Subscription(
                        user_id=1,
                        stripe_customer_id="cus_1",
                        stripe_subscription_id="sub_1",
                        status="active",
                    ),
                    Subscription(
                        user_id=1,
                        stripe_customer_id="cus_1",
                        stripe_subscription_id="sub_2",
                        status="canceled",
                    ),
                ]
            )
            await session.flush()

            result = await session.execute(select(func.count(Subscription.id)))
            assert result.scalar_one() == 2

    run_async(scenario())


def test_enforcing_unique_subscriptions_stripe_subscription_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A Stripe subscription id should be unique."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            session.add_all(
                [
                    Subscription(
                        user_id=1,
                        stripe_customer_id="cus_1",
                        stripe_subscription_id="sub_shared",
                        status="active",
                    ),
                    Subscription(
                        user_id=1,
                        stripe_customer_id="cus_1",
                        stripe_subscription_id="sub_shared",
                        status="canceled",
                    ),
                ]
            )

            try:
                await session.flush()
            except IntegrityError:
                return

            raise AssertionError("Duplicate Stripe subscription id should fail")

    run_async(scenario())


def test_recording_duplicate_stripe_event_only_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Repeated Stripe webhook event ids should be idempotent."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            store = SQLAlchemyBillingStore(session)
            payload = {
                "stripe_event_id": "evt_1",
                "event_type": "customer.subscription.updated",
                "payload_json": {"id": "evt_1"},
            }

            first_result = await store.record_billing_event(payload)
            second_result = await store.record_billing_event(payload)

            assert first_result.created is True
            assert first_result.should_process is True
            assert second_result.created is False
            assert second_result.should_process is False
            assert second_result.event.id == first_result.event.id

            count_result = await session.execute(select(func.count(BillingEvent.id)))
            assert count_result.scalar_one() == 1

    run_async(scenario())


def test_executing_job_status_transitions_with_real_sql_returning(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Job transitions should work through real SQL UPDATE RETURNING."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            store = SQLAlchemyJobStore(session)
            job = await store.create_job(
                {
                    "user_id": 1,
                    "run_id": "run_1",
                    "pipeline_type": "copy_adaptation",
                    "input_json": {"source": "video.mp4"},
                }
            )

            uploaded_job = await store.mark_uploaded(
                job.id,
                {
                    "storage_backend": "local",
                    "input_file_key": "jobs/run_1/input.mp4",
                    "input_file_uri": "/tmp/jobs/run_1/input.mp4",
                },
            )
            running_job = await store.mark_running(job.id, "copy_analysis")
            completed_job = await store.mark_completed(
                job.id,
                {
                    "result": {"script": "final"},
                    "token_usage": {"total": 100},
                    "execution_time_seconds": 12.5,
                },
            )

            assert uploaded_job.status == JOB_STATUS_UPLOADED
            assert running_job.status == JOB_STATUS_RUNNING
            assert completed_job.status == JOB_STATUS_COMPLETED
            assert completed_job.output_json == {"result": {"script": "final"}}

    run_async(scenario())


def test_rolling_back_failed_transactions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A failed outer transaction should not persist partial work."""

    async def scenario() -> None:
        try:
            async with session_factory.begin() as session:
                store = SQLAlchemyUserStore(session)
                await store.create_user(
                    {
                        "email": "rollback@example.com",
                        "password_hash": "hashed-password",
                    }
                )
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        async with session_factory() as session:
            store = SQLAlchemyUserStore(session)
            user = await store.get_user_by_email("rollback@example.com")

        assert user is None

    run_async(scenario())


def test_async_savepoint_scope_with_unique_constraint_conflicts(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A failed savepoint should not poison the outer transaction."""

    async def scenario() -> None:
        async with session_factory.begin() as session:
            session.add(
                User(
                    email="first@example.com",
                    password_hash="hashed-password",
                    auth_provider="password",
                )
            )
            await session.flush()

            try:
                async with async_savepoint_scope(session):
                    session.add(
                        User(
                            email="first@example.com",
                            password_hash="other-hash",
                            auth_provider="password",
                        )
                    )
                    await session.flush()
            except IntegrityError:
                pass
            else:
                raise AssertionError("Duplicate email inside savepoint should fail")

            session.add(
                User(
                    email="second@example.com",
                    password_hash="hashed-password",
                    auth_provider="password",
                )
            )
            await session.flush()

        async with session_factory() as session:
            result = await session.execute(select(func.count(User.id)))
            assert result.scalar_one() == 2

    run_async(scenario())
