"""Unit tests for app user store behavior.

These tests protect user payload validation, normalization, and controlled
error wrapping without requiring a real database connection.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import app.store.users as users
from app.errors import UserStoreError
from app.store.models import User
from app.store.users import SQLAlchemyUserStore


def _run_async(awaitable: Any) -> Any:
    """Run an async store method from a synchronous unit test."""

    return asyncio.run(awaitable)


def _store(session: object | None = None) -> SQLAlchemyUserStore:
    """Build a user store around a typed fake session."""

    return SQLAlchemyUserStore(cast(AsyncSession, session or object()))


class _CreateUserSession:
    """Session fake for create_user without a real database transaction."""

    def __init__(self) -> None:
        self.added: list[User] = []
        self.flush_called = False

    def add(self, instance: User) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flush_called = True


class _ScalarOneOrNoneResult:
    """SQLAlchemy result fake for lookup queries."""

    def __init__(self, value: User | None = None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> User | None:
        return self.value


class _ExecuteCaptureSession:
    """Session fake that captures the executed SQLAlchemy statement."""

    def __init__(self) -> None:
        self.statement: object | None = None

    async def execute(self, statement: object) -> _ScalarOneOrNoneResult:
        self.statement = statement
        return _ScalarOneOrNoneResult()


class _GetRaisesSession:
    """Session fake that raises a SQLAlchemy infrastructure error."""

    async def get(self, model: type[object], model_id: int) -> None:
        raise SQLAlchemyError("database failed")


class _UpdateSpyUserStore(SQLAlchemyUserStore):
    """Store spy that records calls to the internal update helper."""

    def __init__(self) -> None:
        super().__init__(cast(AsyncSession, object()))
        self.update_calls: list[dict[str, Any]] = []

    async def _update_user(
        self,
        *,
        user_id: int,
        operation: str,
        values: Mapping[str, Any],
    ) -> User:
        self.update_calls.append(
            {
                "user_id": user_id,
                "operation": operation,
                "values": dict(values),
            }
        )
        return cast(User, object())


@asynccontextmanager
async def _fake_savepoint(session: object) -> AsyncIterator[object]:
    """Savepoint fake that lets create_user run without SQLAlchemy."""

    yield session


def _compile_query(statement: object) -> str:
    """Compile a SQLAlchemy statement with literals for assertion."""

    compiled = getattr(statement, "compile")
    return str(compiled(compile_kwargs={"literal_binds": True}))


def test_create_user_requires_email() -> None:
    """create_user should reject missing or blank email values."""

    store = _store()

    for payload in ({}, {"email": "   "}):
        with pytest.raises(UserStoreError) as error:
            _run_async(store.create_user(payload))

        assert error.value.details == {
            "operation": "create_user",
            "field": "email",
        }


def test_create_user_rejects_invalid_email() -> None:
    """create_user should reject email values without an at sign."""

    store = _store()

    with pytest.raises(UserStoreError) as error:
        _run_async(
            store.create_user(
                {
                    "email": "invalid-email",
                    "password_hash": "hashed-password",
                }
            )
        )

    assert error.value.details == {
        "operation": "create_user",
        "field": "email",
    }


def test_create_user_normalizes_email_to_lowercase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_user should persist normalized lowercase emails."""

    monkeypatch.setattr(users, "async_savepoint_scope", _fake_savepoint)
    session = _CreateUserSession()
    store = _store(session)

    user = cast(
        User,
        _run_async(
            store.create_user(
                {
                    "email": "USER@EXAMPLE.COM",
                    "password_hash": "hashed-password",
                }
            )
        ),
    )

    assert user.email == "user@example.com"
    assert session.added == [user]
    assert session.flush_called is True


def test_create_password_user_requires_password_hash() -> None:
    """Password users should never be created without a password hash."""

    store = _store()

    with pytest.raises(UserStoreError) as error:
        _run_async(
            store.create_user(
                {
                    "email": "user@example.com",
                    "auth_provider": users.DEFAULT_AUTH_PROVIDER,
                }
            )
        )

    assert error.value.details == {
        "operation": "create_user",
        "field": "password_hash",
    }


def test_create_google_user_requires_google_sub() -> None:
    """Google users require the provider subject identifier."""

    store = _store()

    with pytest.raises(UserStoreError) as error:
        _run_async(
            store.create_user(
                {
                    "email": "user@example.com",
                    "auth_provider": users.GOOGLE_AUTH_PROVIDER,
                }
            )
        )

    assert error.value.details == {
        "operation": "create_user",
        "field": "google_sub",
    }


def test_create_google_user_allows_null_password_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth users should be valid without a local password hash."""

    monkeypatch.setattr(users, "async_savepoint_scope", _fake_savepoint)
    session = _CreateUserSession()
    store = _store(session)

    user = cast(
        User,
        _run_async(
            store.create_user(
                {
                    "email": "oauth@example.com",
                    "auth_provider": users.GOOGLE_AUTH_PROVIDER,
                    "google_sub": "google-sub-123",
                }
            )
        ),
    )

    assert user.email == "oauth@example.com"
    assert user.auth_provider == users.GOOGLE_AUTH_PROVIDER
    assert user.google_sub == "google-sub-123"
    assert user.password_hash is None
    assert session.added == [user]
    assert session.flush_called is True


def test_get_user_by_email_normalizes_email_before_query() -> None:
    """get_user_by_email should query using the normalized email value."""

    session = _ExecuteCaptureSession()
    store = _store(session)

    result = _run_async(store.get_user_by_email(" USER@EXAMPLE.COM "))

    assert result is None
    assert session.statement is not None
    assert "users.email = 'user@example.com'" in _compile_query(session.statement)


def test_get_user_by_google_sub_rejects_blank_google_sub() -> None:
    """get_user_by_google_sub should reject blank provider identifiers."""

    store = _store()

    with pytest.raises(UserStoreError) as error:
        _run_async(store.get_user_by_google_sub("   "))

    assert error.value.details == {
        "operation": "get_user_by_google_sub",
        "field": "google_sub",
    }


def test_update_password_hash_rejects_blank_hash() -> None:
    """update_password_hash should reject empty password hash values."""

    store = _store()

    with pytest.raises(UserStoreError) as error:
        _run_async(store.update_password_hash(1, "   "))

    assert error.value.details == {
        "operation": "update_password_hash",
        "field": "password_hash",
    }


def test_mark_email_verified_updates_with_database_time() -> None:
    """mark_email_verified should delegate to the update helper with db time."""

    store = _UpdateSpyUserStore()

    _run_async(store.mark_email_verified(7))

    assert store.update_calls[0]["user_id"] == 7
    assert store.update_calls[0]["operation"] == "mark_email_verified"
    assert "email_verified_at" in store.update_calls[0]["values"]


def test_sqlalchemy_errors_are_wrapped_as_user_store_error() -> None:
    """SQLAlchemy infrastructure errors should become controlled store errors."""

    store = _store(_GetRaisesSession())

    with pytest.raises(UserStoreError) as error:
        _run_async(store.get_user(123))

    assert error.value.details == {
        "operation": "get_user",
        "user_id": 123,
        "error_type": "SQLAlchemyError",
    }
