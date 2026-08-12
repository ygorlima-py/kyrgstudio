"""SQLAlchemy persistence for password-reset tokens.

This module stores only deterministic token hashes. Raw password-reset tokens,
password hashing, email delivery, transaction ownership, and HTTP behavior
belong to higher application layers.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import StoreError
from app.store.base import PasswordResetStoreBase
from app.store.database import async_savepoint_scope
from app.store.models import PasswordResetToken


class SQLAlchemyPasswordResetStore(PasswordResetStoreBase):
    """Persist and atomically consume single-use password-reset tokens.

    The caller owns commit and rollback. This allows token consumption,
    password replacement, and session revocation to share one transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        """Persist one token hash without committing the transaction."""

        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(token)
                await self.session.flush()
        except IntegrityError as error:
            raise _password_reset_store_error(
                "create_password_reset_token",
                "Password-reset token violates a database constraint.",
                error=error,
            )
        except (SQLAlchemyError, ValueError) as error:
            raise _password_reset_store_error(
                "create_password_reset_token",
                "Failed to create password-reset token.",
                error=error,
            )

        return token

    async def get_token_by_hash(
        self,
        *,
        token_hash: str,
    ) -> PasswordResetToken | None:
        """Return one token by hash without exposing it in error metadata."""

        statement = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )

        try:
            result = await self.session.execute(statement)
        except SQLAlchemyError as error:
            raise _password_reset_store_error(
                "get_password_reset_token_by_hash",
                "Failed to load password-reset token.",
                error=error,
            )

        return result.scalar_one_or_none()

    async def consume_token(
        self,
        *,
        token_hash: str,
        consumed_at: datetime,
    ) -> PasswordResetToken:
        """Consume a token only when it is unused and has not expired.

        The conditions and the update execute in one SQL statement. Concurrent
        requests therefore cannot successfully consume the same token twice.
        """

        statement = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > consumed_at,
            )
            .values(used_at=consumed_at)
            .returning(PasswordResetToken)
        )

        try:
            result = await self.session.execute(statement)
        except SQLAlchemyError as error:
            raise _password_reset_store_error(
                "consume_password_reset_token",
                "Failed to consume password-reset token.",
                error=error,
            )

        token = result.scalar_one_or_none()

        if token is None:
            raise StoreError(
                technical_message=(
                    "Password-reset token is missing, expired, or already used."
                ),
                details={
                    "operation": "consume_password_reset_token",
                    "reason": "unavailable",
                },
            )

        return token

    async def revoke_pending_tokens_for_user(
        self,
        *,
        user_id: int,
        revoked_at: datetime,
    ) -> int:
        """Invalidate all unused tokens belonging to one user."""

        statement = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=revoked_at)
        )

        try:
            result = await self.session.execute(statement)
        except SQLAlchemyError as error:
            raise _password_reset_store_error(
                "revoke_pending_password_reset_tokens",
                "Failed to revoke pending password-reset tokens.",
                error=error,
            )

        return _affected_row_count(result)

    async def delete_expired_tokens(
        self,
        *,
        before: datetime,
    ) -> int:
        """Delete tokens whose expiration is not later than ``before``."""

        statement = delete(PasswordResetToken).where(
            PasswordResetToken.expires_at <= before
        )

        try:
            result = await self.session.execute(statement)
        except SQLAlchemyError as error:
            raise _password_reset_store_error(
                "delete_expired_password_reset_tokens",
                "Failed to delete expired password-reset tokens.",
                error=error,
            )

        return _affected_row_count(result)


def _affected_row_count(result: object) -> int:
    """Return the number of rows changed by an UPDATE or DELETE statement."""

    cursor_result = cast(CursorResult, result)
    return cursor_result.rowcount or 0


def _password_reset_store_error(
    operation: str,
    technical_message: str,
    *,
    error: Exception,
) -> StoreError:
    """Build a controlled store error without leaking token material."""

    return StoreError(
        technical_message=technical_message,
        details={
            "operation": operation,
            "error_type": type(error).__name__,
        },
    )


__all__ = ["SQLAlchemyPasswordResetStore"]
