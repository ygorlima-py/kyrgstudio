"""Create application store tables.

Revision ID: 0001_create_app_store_tables
Revises:
Create Date: 2026-07-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_app_store_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial application persistence schema."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("auth_provider", sa.String(length=50), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    op.create_table(
        "billing_customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_billing_customers_user_id",
        "billing_customers",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_customers_stripe_customer_id",
        "billing_customers",
        ["stripe_customer_id"],
        unique=True,
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
    )

    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])
    op.create_index("ix_billing_events_created_at", "billing_events", ["created_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=False),
        sa.Column("pipeline_type", sa.String(length=50), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("storage_backend", sa.String(length=50), nullable=True),
        sa.Column("input_file_key", sa.String(length=1024), nullable=True),
        sa.Column("input_file_uri", sa.String(length=2048), nullable=True),
        sa.Column("audio_file_key", sa.String(length=1024), nullable=True),
        sa.Column("audio_file_uri", sa.String(length=2048), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("token_usage_json", sa.JSON(), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_index("ix_job_events_created_at", "job_events", ["created_at"])
    op.create_index(
        "ix_job_events_job_id_created_at",
        "job_events",
        ["job_id", "created_at"],
    )


def downgrade() -> None:
    """Drop the application persistence schema."""

    op.drop_index("ix_job_events_job_id_created_at", table_name="job_events")
    op.drop_index("ix_job_events_created_at", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_billing_events_created_at", table_name="billing_events")
    op.drop_index("ix_billing_events_event_type", table_name="billing_events")
    op.drop_table("billing_events")

    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(
        "ix_billing_customers_stripe_customer_id",
        table_name="billing_customers",
    )
    op.drop_index("ix_billing_customers_user_id", table_name="billing_customers")
    op.drop_table("billing_customers")

    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
