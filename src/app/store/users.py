"""User persistence for the application store.

This module persists user records only. Authentication flows, password hashing,
JWT/session management, OAuth validation, and permission checks belong to higher
application layers.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import UserStoreError
from app.store.base import UserStoreBase
from app.store.database import async_savepoint_scope
from app.store.models import User


DEFAULT_AUTH_PROVIDER = "password"
GOOGLE_AUTH_PROVIDER = "google"


class SQLAlchemyUserStore(UserStoreBase):
    """SQLAlchemy implementation of user persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, payload: dict[str, Any]) -> User:
        """Create a user from normalized application input.

        The caller must pass a password hash, never a plain password. OAuth users
        may have ``password_hash=None`` when the provider allows passwordless
        login.
        """

        operation = "create_user"
        email = _required_email(payload, "email", operation=operation)
        auth_provider = (
            _optional_str(payload.get("auth_provider")) or DEFAULT_AUTH_PROVIDER
        )
        password_hash = _optional_str(payload.get("password_hash"))
        google_sub = _optional_str(payload.get("google_sub"))

        if auth_provider == DEFAULT_AUTH_PROVIDER and password_hash is None:
            raise UserStoreError(
                technical_message="Password users require password_hash.",
                details={"operation": operation, "field": "password_hash"},
            )

        if auth_provider == GOOGLE_AUTH_PROVIDER and google_sub is None:
            raise UserStoreError(
                technical_message="Google users require google_sub.",
                details={"operation": operation, "field": "google_sub"},
            )

        user = User(
            email=email,
            password_hash=password_hash,
            name=_optional_str(payload.get("name")),
            avatar_url=_optional_str(payload.get("avatar_url")),
            auth_provider=auth_provider,
            google_sub=google_sub,
            email_verified_at=_optional_datetime(payload.get("email_verified_at")),
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(user)
                await self.session.flush()
        except IntegrityError as error:
            raise _user_store_error(
                operation,
                "User already exists or violates a unique constraint.",
                details={"conflict_fields": ["email", "google_sub"]},
                error=error,
            )
        except (SQLAlchemyError, ValueError) as error:
            raise _user_store_error(
                operation,
                "Failed to create user.",
                error=error,
            )

        return user

    async def get_user(self, user_id: int) -> User | None:
        """Return a user by internal id, or ``None`` when absent."""

        operation = "get_user"

        try:
            return await self.session.get(User, user_id)
        except SQLAlchemyError as error:
            raise _user_store_error(
                operation,
                "Failed to get user.",
                details={"user_id": user_id},
                error=error,
            )

    async def get_user_by_email(self, email: str) -> User | None:
        """Return a user by normalized email, or ``None`` when absent."""

        operation = "get_user_by_email"
        normalized_email = _normalize_email(email, operation=operation)

        try:
            result = await self.session.execute(
                select(User).where(User.email == normalized_email)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _user_store_error(
                operation,
                "Failed to get user by email.",
                error=error,
            )

    async def get_user_by_google_sub(self, google_sub: str) -> User | None:
        """Return a user by Google subject id, or ``None`` when absent."""

        operation = "get_user_by_google_sub"
        normalized_google_sub = _required_value(
            google_sub,
            "google_sub",
            operation=operation,
        )

        try:
            result = await self.session.execute(
                select(User).where(User.google_sub == normalized_google_sub)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _user_store_error(
                operation,
                "Failed to get user by google_sub.",
                error=error,
            )

    async def update_password_hash(self, user_id: int, password_hash: str) -> User:
        """Replace a user's password hash.

        This method expects an already-hashed password. It never receives or
        stores a plain password.
        """

        operation = "update_password_hash"
        normalized_password_hash = _required_value(
            password_hash,
            "password_hash",
            operation=operation,
        )

        return await self._update_user(
            user_id=user_id,
            operation=operation,
            values={"password_hash": normalized_password_hash},
        )

    async def mark_email_verified(self, user_id: int) -> User:
        """Mark a user's email as verified using database time."""

        operation = "mark_email_verified"

        return await self._update_user(
            user_id=user_id,
            operation=operation,
            values={"email_verified_at": func.now()},
        )

    async def _update_user(
        self,
        *,
        user_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> User:
        """Apply an atomic user update and return the updated row."""

        update_values = dict(values)
        update_values["updated_at"] = func.now()

        try:
            result = await self.session.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_values)
                .returning(User.id)
            )
            updated_user_id = result.scalar_one_or_none()

            if updated_user_id is None:
                raise UserStoreError(
                    technical_message="User was not found for update.",
                    details={"operation": operation, "user_id": user_id},
                )

            user = await self.get_user(updated_user_id)

            if user is None:
                raise UserStoreError(
                    technical_message="Updated user was not found after update.",
                    details={"operation": operation, "user_id": updated_user_id},
                )

            return user
        except UserStoreError:
            raise
        except SQLAlchemyError as error:
            raise _user_store_error(
                operation,
                "Failed to update user.",
                details={"user_id": user_id},
                error=error,
            )


UserStore = SQLAlchemyUserStore


def _required_email(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> str:
    value = payload.get(field)
    return _normalize_email(value, operation=operation, field=field)


def _normalize_email(
    value: Any,
    *,
    operation: str,
    field: str = "email",
) -> str:
    normalized = _required_value(value, field, operation=operation).lower()

    if "@" not in normalized:
        raise UserStoreError(
            technical_message="Invalid email address.",
            details={"operation": operation, "field": field},
        )

    return normalized


def _required_value(value: Any, field: str, *, operation: str) -> str:
    if value is None:
        raise UserStoreError(
            technical_message=f"Required user field is missing: {field}",
            details={"operation": operation, "field": field},
        )

    normalized = str(value).strip()

    if normalized == "":
        raise UserStoreError(
            technical_message=f"Required user field is empty: {field}",
            details={"operation": operation, "field": field},
        )

    return normalized


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _optional_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value

    raise UserStoreError(
        technical_message="email_verified_at must be a datetime value.",
        details={"operation": "create_user", "field": "email_verified_at"},
    )


def _user_store_error(
    operation: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> UserStoreError:
    error_details = {"operation": operation}
    error_details.update(details or {})

    if error is not None:
        error_details["error_type"] = error.__class__.__name__

    return UserStoreError(
        technical_message=message,
        details=error_details,
    )


__all__ = [
    "DEFAULT_AUTH_PROVIDER",
    "GOOGLE_AUTH_PROVIDER",
    "SQLAlchemyUserStore",
    "UserStore",
]
