"""Unit tests for app store SQLAlchemy model metadata.

These tests validate the database contract represented by the model metadata.
They do not open a database connection and do not depend on Alembic or a real
Postgres instance.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Column, String

from app.store.models import (
    Base,
    BillingCustomer,
    BillingEvent,
    Job,
    JobEvent,
    Subscription,
    User,
)


def _column(model: Any, name: str) -> Column[Any]:
    """Return a SQLAlchemy column by name from a mapped model."""

    return model.__table__.c[name]


def _column_names(model: Any) -> set[str]:
    """Return all column names from a mapped model table."""

    return set(model.__table__.columns.keys())


def _index_column_sets(model: Any) -> set[tuple[str, ...]]:
    """Return table indexes represented as ordered column-name tuples."""

    return {
        tuple(column.name for column in index.columns)
        for index in model.__table__.indexes
    }


def _assert_has_columns(model: Any, expected: set[str]) -> None:
    """Assert that a model has every column required by the schema contract."""

    assert expected <= _column_names(model)


def _assert_column_is_indexed(model: Any, column_name: str) -> None:
    """Assert that a single-column index exists for a model column."""

    column = _column(model, column_name)
    assert column.index is True or (column_name,) in _index_column_sets(model)


def test_users_table_name_and_columns() -> None:
    """The users table should expose all fields needed by auth and ownership."""

    assert User.__tablename__ == "users"
    _assert_has_columns(
        User,
        {
            "id",
            "email",
            "password_hash",
            "name",
            "avatar_url",
            "auth_provider",
            "google_sub",
            "email_verified_at",
            "created_at",
            "updated_at",
            "disabled_at",
        },
    )


def test_users_email_is_unique_and_uses_expected_length() -> None:
    """Email should be globally unique and use the RFC-compatible max length."""

    email = _column(User, "email")
    email_type = cast(String, email.type)

    assert email.unique is True
    assert email_type.length == 320


def test_users_google_sub_is_unique_and_indexed() -> None:
    """Google OAuth subject should support unique lookup."""

    google_sub = _column(User, "google_sub")

    assert google_sub.unique is True
    _assert_column_is_indexed(User, "google_sub")


def test_users_password_hash_is_nullable_for_oauth_users() -> None:
    """OAuth-only users should not require a local password hash."""

    assert _column(User, "password_hash").nullable is True


def test_billing_customers_table_name_and_columns() -> None:
    """Billing customers should link local users to Stripe customers."""

    assert BillingCustomer.__tablename__ == "billing_customers"
    _assert_has_columns(
        BillingCustomer,
        {
            "id",
            "user_id",
            "stripe_customer_id",
            "created_at",
            "updated_at",
        },
    )


def test_billing_customers_constraints() -> None:
    """A Stripe customer should have a one-to-one local user mapping."""

    user_id = _column(BillingCustomer, "user_id")
    stripe_customer_id = _column(BillingCustomer, "stripe_customer_id")
    foreign_keys = {foreign_key.target_fullname for foreign_key in user_id.foreign_keys}

    assert user_id.unique is True
    assert stripe_customer_id.unique is True
    _assert_column_is_indexed(BillingCustomer, "user_id")
    _assert_column_is_indexed(BillingCustomer, "stripe_customer_id")
    assert foreign_keys == {"users.id"}


def test_subscriptions_table_name_and_columns() -> None:
    """Subscriptions should represent Stripe subscription state and periods."""

    assert Subscription.__tablename__ == "subscriptions"
    _assert_has_columns(
        Subscription,
        {
            "id",
            "user_id",
            "stripe_customer_id",
            "stripe_subscription_id",
            "stripe_price_id",
            "status",
            "plan",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "created_at",
            "updated_at",
        },
    )


def test_subscriptions_customer_id_is_indexed_but_not_unique() -> None:
    """Customer id should be searchable while allowing subscription history."""

    stripe_customer_id = _column(Subscription, "stripe_customer_id")

    assert stripe_customer_id.unique is not True
    _assert_column_is_indexed(Subscription, "stripe_customer_id")


def test_subscriptions_subscription_id_is_unique() -> None:
    """Stripe subscription id should be the unique natural subscription key."""

    assert _column(Subscription, "stripe_subscription_id").unique is True


def test_billing_events_table_name_and_columns() -> None:
    """Billing events should persist Stripe webhook event metadata."""

    assert BillingEvent.__tablename__ == "billing_events"
    _assert_has_columns(
        BillingEvent,
        {
            "id",
            "stripe_event_id",
            "event_type",
            "payload_json",
            "processed_at",
            "created_at",
        },
    )


def test_billing_events_idempotency_constraints() -> None:
    """Stripe event id should provide webhook idempotency."""

    assert _column(BillingEvent, "stripe_event_id").unique is True
    _assert_column_is_indexed(BillingEvent, "event_type")
    _assert_column_is_indexed(BillingEvent, "created_at")


def test_jobs_table_name_and_columns() -> None:
    """Jobs should store product execution state and result references."""

    assert Job.__tablename__ == "jobs"
    _assert_has_columns(
        Job,
        {
            "id",
            "user_id",
            "run_id",
            "status",
            "current_step",
            "pipeline_type",
            "input_json",
            "storage_backend",
            "input_file_key",
            "input_file_uri",
            "audio_file_key",
            "audio_file_uri",
            "output_json",
            "error_json",
            "token_usage_json",
            "execution_time_seconds",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        },
    )


def test_jobs_indices_and_uniques() -> None:
    """Jobs should support owner, status, chronological, and idempotency lookup."""

    _assert_column_is_indexed(Job, "user_id")
    _assert_column_is_indexed(Job, "status")
    _assert_column_is_indexed(Job, "created_at")
    assert _column(Job, "run_id").unique is True


def test_job_events_table_name_and_columns() -> None:
    """Job events should store small status/history events for a job."""

    assert JobEvent.__tablename__ == "job_events"
    _assert_has_columns(
        JobEvent,
        {
            "id",
            "job_id",
            "step",
            "event_type",
            "payload_json",
            "created_at",
        },
    )


def test_job_events_has_compound_index_for_history_lookup() -> None:
    """Job history lookup should be indexed by job id and creation time."""

    assert ("job_id", "created_at") in _index_column_sets(JobEvent)


def test_model_metadata_contains_all_store_tables() -> None:
    """Store metadata should include every planned table for migrations."""

    assert {
        "users",
        "billing_customers",
        "subscriptions",
        "billing_events",
        "jobs",
        "job_events",
    } <= set(Base.metadata.tables.keys())
