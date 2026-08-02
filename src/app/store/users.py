"""User and authentication-session persistence for the application store.

This module stores user records and hashed refresh-token sessions. Password
hashing, JWT encoding, OAuth validation, authentication policy, and transaction
ownership remain in higher application layers.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import StoreError, UserStoreError
from app.store.base import AuthSessionStoreBase, UserStoreBase
from app.store.database import async_savepoint_scope
from app.store.models import AuthSession, User


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


class SQLAlchemyAuthSessionStore(AuthSessionStoreBase):
    """Persist refresh-token sessions without owning transaction boundaries.

    The caller controls commit and rollback. Rotation uses a row lock and a
    savepoint so one refresh session cannot be replaced concurrently by two
    requests.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        payload: dict[str, Any],
    ) -> AuthSession:
        """Create a refresh session from a token digest and expiry metadata."""

        operation = "create_auth_session"
        user_id = _required_positive_identifier(
            payload.get("user_id"),
            "user_id",
            operation=operation,
        )
        token_hash = _required_auth_session_text(
            payload.get("token_hash"),
            "token_hash",
            operation=operation,
            max_length=128,
        )
        family_id = _required_auth_session_text(
            payload.get("family_id"),
            "family_id",
            operation=operation,
            max_length=36,
        )
        expires_at = _required_auth_session_datetime(
            payload.get("expires_at"),
            "expires_at",
            operation=operation,
        )
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(auth_session)
                await self.session.flush()
        except IntegrityError as error:
            raise _auth_session_store_error(
                operation,
                "Auth session violates a database constraint.",
                details={"user_id": user_id},
                error=error,
            )
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to create auth session.",
                details={"user_id": user_id},
                error=error,
            )

        return auth_session

    async def get_session(
        self,
        session_id: int,
    ) -> AuthSession | None:
        """Return one auth session by internal id."""

        operation = "get_auth_session"
        normalized_session_id = _required_positive_identifier(
            session_id,
            "session_id",
            operation=operation,
        )

        try:
            return await self.session.get(AuthSession, normalized_session_id)
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to get auth session.",
                details={"session_id": normalized_session_id},
                error=error,
            )

    async def get_session_by_token_hash(
        self,
        token_hash: str,
        *,
        lock_for_update: bool = False,
    ) -> AuthSession | None:
        """Return a session by token digest, optionally locking the row.

        ``lock_for_update=True`` is effective only inside a caller-owned
        transaction and is required before security-sensitive refresh
        decisions.
        """

        operation = "get_auth_session_by_token_hash"
        normalized_token_hash = _required_auth_session_text(
            token_hash,
            "token_hash",
            operation=operation,
            max_length=128,
        )
        statement = select(AuthSession).where(
            AuthSession.token_hash == normalized_token_hash
        )

        if lock_for_update:
            statement = statement.with_for_update()

        try:
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to get auth session by token hash.",
                error=error,
            )

    async def rotate_session(
        self,
        session_id: int,
        replacement: dict[str, Any],
    ) -> AuthSession:
        """Atomically revoke one session and create its replacement.

        The replacement remains in the same user and token family. Expiration
        and replay policy decisions remain the responsibility of ``AuthService``.
        """

        operation = "rotate_auth_session"
        normalized_session_id = _required_positive_identifier(
            session_id,
            "session_id",
            operation=operation,
        )
        replacement_token_hash = _required_auth_session_text(
            replacement.get("token_hash"),
            "token_hash",
            operation=operation,
            max_length=128,
        )
        replacement_expires_at = _required_auth_session_datetime(
            replacement.get("expires_at"),
            "expires_at",
            operation=operation,
        )

        try:
            async with async_savepoint_scope(self.session):
                current_session = await self._get_session_for_update(
                    normalized_session_id,
                    operation=operation,
                )

                if (
                    current_session.revoked_at is not None
                    or current_session.replaced_by_session_id is not None
                ):
                    raise _auth_session_store_error(
                        operation,
                        "Auth session has already been rotated or revoked.",
                        details={"session_id": normalized_session_id},
                    )

                replacement_session = AuthSession(
                    user_id=current_session.user_id,
                    token_hash=replacement_token_hash,
                    family_id=current_session.family_id,
                    expires_at=replacement_expires_at,
                )
                self.session.add(replacement_session)
                await self.session.flush()

                result = await self.session.execute(
                    update(AuthSession)
                    .where(
                        AuthSession.id == normalized_session_id,
                        AuthSession.revoked_at.is_(None),
                        AuthSession.replaced_by_session_id.is_(None),
                    )
                    .values(
                        revoked_at=func.now(),
                        last_used_at=func.now(),
                        replaced_by_session_id=replacement_session.id,
                    )
                    .returning(AuthSession.id)
                )

                if result.scalar_one_or_none() is None:
                    raise _auth_session_store_error(
                        operation,
                        "Auth session changed during rotation.",
                        details={"session_id": normalized_session_id},
                    )

                # The bulk UPDATE uses database expressions such as now(), so
                # SQLAlchemy expires the affected attributes. Reload them
                # asynchronously before this model leaves the store boundary.
                await self.session.refresh(current_session)
                return replacement_session
        except StoreError:
            raise
        except IntegrityError as error:
            raise _auth_session_store_error(
                operation,
                "Replacement auth session violates a database constraint.",
                details={"session_id": normalized_session_id},
                error=error,
            )
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to rotate auth session.",
                details={"session_id": normalized_session_id},
                error=error,
            )

    async def revoke_session(self, session_id: int) -> AuthSession:
        """Revoke one auth session idempotently."""

        operation = "revoke_auth_session"
        normalized_session_id = _required_positive_identifier(
            session_id,
            "session_id",
            operation=operation,
        )

        try:
            result = await self.session.execute(
                update(AuthSession)
                .where(
                    AuthSession.id == normalized_session_id,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=func.now())
                .returning(AuthSession.id)
            )
            updated_session_id = result.scalar_one_or_none()

            auth_session = await self.get_session(
                updated_session_id or normalized_session_id
            )

            if auth_session is None:
                raise _auth_session_store_error(
                    operation,
                    "Auth session was not found for revocation.",
                    details={"session_id": normalized_session_id},
                )

            await self.session.refresh(auth_session)
            return auth_session
        except StoreError:
            raise
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to revoke auth session.",
                details={"session_id": normalized_session_id},
                error=error,
            )

    async def revoke_user_sessions(self, user_id: int) -> int:
        """Revoke every active refresh session owned by one user."""

        operation = "revoke_user_auth_sessions"
        normalized_user_id = _required_positive_identifier(
            user_id,
            "user_id",
            operation=operation,
        )

        return await self._revoke_matching_sessions(
            operation=operation,
            conditions=(AuthSession.user_id == normalized_user_id,),
            details={"user_id": normalized_user_id},
        )

    async def revoke_family(self, family_id: str) -> int:
        """Revoke every active session in one refresh-token family."""

        operation = "revoke_auth_session_family"
        normalized_family_id = _required_auth_session_text(
            family_id,
            "family_id",
            operation=operation,
            max_length=36,
        )

        return await self._revoke_matching_sessions(
            operation=operation,
            conditions=(AuthSession.family_id == normalized_family_id,),
        )

    async def _get_session_for_update(
        self,
        session_id: int,
        *,
        operation: str,
    ) -> AuthSession:
        result = await self.session.execute(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
        )
        auth_session = result.scalar_one_or_none()

        if auth_session is None:
            raise _auth_session_store_error(
                operation,
                "Auth session was not found.",
                details={"session_id": session_id},
            )

        return auth_session

    async def _revoke_matching_sessions(
        self,
        *,
        operation: str,
        conditions: tuple[Any, ...],
        details: dict[str, Any] | None = None,
    ) -> int:
        try:
            result = await self.session.execute(
                update(AuthSession)
                .where(
                    *conditions,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=func.now())
                .returning(AuthSession.id)
            )
            return len(result.scalars().all())
        except SQLAlchemyError as error:
            raise _auth_session_store_error(
                operation,
                "Failed to revoke auth sessions.",
                details=details,
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


def _required_positive_identifier(
    value: Any,
    field: str,
    *,
    operation: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _auth_session_store_error(
            operation,
            f"{field} must be a positive integer.",
            details={"field": field},
        )

    return value


def _required_auth_session_text(
    value: Any,
    field: str,
    *,
    operation: str,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise _auth_session_store_error(
            operation,
            f"{field} must be a string.",
            details={"field": field},
        )

    normalized = value.strip()

    if not normalized:
        raise _auth_session_store_error(
            operation,
            f"{field} must not be blank.",
            details={"field": field},
        )

    if len(normalized) > max_length:
        raise _auth_session_store_error(
            operation,
            f"{field} exceeds its maximum length.",
            details={"field": field, "maximum": max_length},
        )

    return normalized


def _required_auth_session_datetime(
    value: Any,
    field: str,
    *,
    operation: str,
) -> datetime:
    if not isinstance(value, datetime):
        raise _auth_session_store_error(
            operation,
            f"{field} must be a datetime value.",
            details={"field": field},
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise _auth_session_store_error(
            operation,
            f"{field} must include timezone information.",
            details={"field": field},
        )

    return value


def _auth_session_store_error(
    operation: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> StoreError:
    error_details = {"operation": operation}
    error_details.update(details or {})

    if error is not None:
        error_details["error_type"] = error.__class__.__name__

    return StoreError(
        technical_message=message,
        details=error_details,
    )


__all__ = [
    "DEFAULT_AUTH_PROVIDER",
    "GOOGLE_AUTH_PROVIDER",
    "SQLAlchemyAuthSessionStore",
    "SQLAlchemyUserStore",
    "UserStore",
]
