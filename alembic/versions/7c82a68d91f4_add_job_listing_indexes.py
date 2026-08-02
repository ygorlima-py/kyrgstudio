"""add job listing indexes

Revision ID: 7c82a68d91f4
Revises: 0247a04983f0
Create Date: 2026-08-02

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "7c82a68d91f4"
down_revision: str | Sequence[str] | None = "0247a04983f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Index authenticated job history filters and newest-first ordering."""

    op.create_index(
        "ix_jobs_user_created_id",
        "jobs",
        ["user_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_user_status_created_id",
        "jobs",
        ["user_id", "status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_user_pipeline_created_id",
        "jobs",
        ["user_id", "pipeline_type", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove indexes dedicated to authenticated job history queries."""

    op.drop_index("ix_jobs_user_pipeline_created_id", table_name="jobs")
    op.drop_index("ix_jobs_user_status_created_id", table_name="jobs")
    op.drop_index("ix_jobs_user_created_id", table_name="jobs")
