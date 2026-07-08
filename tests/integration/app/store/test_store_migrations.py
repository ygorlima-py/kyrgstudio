"""Integration tests for app store Alembic migrations."""

from __future__ import annotations

from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from _helpers import (
    inspect_database,
    make_alembic_config,
    upgrade_database,
)


EXPECTED_STORE_TABLES = {
    "users",
    "billing_customers",
    "subscriptions",
    "billing_events",
    "jobs",
    "job_events",
}


def test_creating_all_tables_from_alembic_migrations(
    migrated_database_url: str,
) -> None:
    """Alembic migrations should create every app store table."""

    def table_names(connection: Connection) -> set[str]:
        return set(inspect(connection).get_table_names())

    tables = inspect_database(migrated_database_url, table_names)

    assert EXPECTED_STORE_TABLES <= tables


def test_applying_first_migration_from_empty_database(
    empty_database_url: str,
) -> None:
    """A fresh database should upgrade to the current Alembic head."""

    upgrade_database(empty_database_url)

    def current_revision(connection: Connection) -> str:
        result = connection.execute(text("select version_num from alembic_version"))
        return str(result.scalar_one())

    config = make_alembic_config(empty_database_url)
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    database_revision = inspect_database(empty_database_url, current_revision)

    assert database_revision == head_revision == "0001_create_app_store_tables"


def test_verifying_indexes_exist_in_migrated_database(
    migrated_database_url: str,
) -> None:
    """Migrated tables should contain the indexes needed by store queries."""

    expected_indexes = {
        "users": {"ix_users_google_sub"},
        "billing_customers": {
            "ix_billing_customers_user_id",
            "ix_billing_customers_stripe_customer_id",
        },
        "subscriptions": {
            "ix_subscriptions_user_id",
            "ix_subscriptions_stripe_customer_id",
        },
        "billing_events": {
            "ix_billing_events_event_type",
            "ix_billing_events_created_at",
        },
        "jobs": {
            "ix_jobs_user_id",
            "ix_jobs_status",
            "ix_jobs_created_at",
        },
        "job_events": {
            "ix_job_events_created_at",
            "ix_job_events_job_id_created_at",
        },
    }

    def indexes_by_table(connection: Connection) -> dict[str, set[str]]:
        inspector = inspect(connection)
        return {
            table_name: {
                str(index["name"])
                for index in inspector.get_indexes(table_name)
                if index.get("name") is not None
            }
            for table_name in expected_indexes
        }

    actual_indexes = inspect_database(migrated_database_url, indexes_by_table)

    for table_name, index_names in expected_indexes.items():
        assert index_names <= actual_indexes[table_name]
