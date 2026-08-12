"""Unit tests for the short-lived transactional authentication store."""

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, TypeVar, cast

import pytest

import app.auth.transactional_store as transactional_store
from app.auth.transactional_store import (
    AuthSessionRecord,
    AuthStore,
    AuthUserRecord,
    PasswordResetTokenRecord,
)
from app.errors import StoreError, UserStoreError
from app.store.database import SessionFactory


ResultT = TypeVar("ResultT")
NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _user_model(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 7,
        "email": "user@example.com",
        "password_hash": "argon2-hash",
        "name": "Ada",
        "avatar_url": None,
        "auth_provider": "password",
        "google_sub": None,
        "email_verified_at": NOW,
        "disabled_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _session_model(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 13,
        "user_id": 7,
        "token_hash": "token-hash",
        "family_id": "family-id",
        "expires_at": NOW + timedelta(days=30),
        "last_used_at": NOW,
        "revoked_at": None,
        "replaced_by_session_id": None,
        "created_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _password_reset_token_model(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 29,
        "user_id": 7,
        "token_hash": "password-reset-token-hash",
        "expires_at": NOW + timedelta(minutes=30),
        "used_at": None,
        "created_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeUserStore:
    """Configurable SQLAlchemy user-store replacement."""

    def __init__(self, session: object) -> None:
        self.session = session
        self.calls: list[tuple[str, object]] = []
        self.user: SimpleNamespace | None = _user_model()

    async def get_user(self, user_id: int) -> SimpleNamespace | None:
        self.calls.append(("get_user", user_id))
        return self.user

    async def get_user_by_email(self, email: str) -> SimpleNamespace | None:
        self.calls.append(("get_user_by_email", email))
        return self.user

    async def get_user_by_google_sub(
        self,
        subject: str,
    ) -> SimpleNamespace | None:
        self.calls.append(("get_user_by_google_sub", subject))
        return self.user

    async def create_user(self, payload: dict[str, Any]) -> SimpleNamespace:
        self.calls.append(("create_user", payload))
        assert self.user is not None
        return self.user

    async def update_password_hash(
        self,
        user_id: int,
        password_hash: str,
    ) -> SimpleNamespace:
        self.calls.append(
            ("update_password_hash", (user_id, password_hash))
        )
        assert self.user is not None
        self.user.password_hash = password_hash
        return self.user


class FakeAuthSessionStore:
    """Configurable SQLAlchemy auth-session store replacement."""

    def __init__(self, session: object) -> None:
        self.session = session
        self.calls: list[tuple[str, object]] = []
        self.current_session: SimpleNamespace | None = _session_model()
        self.replacement_session = _session_model(
            id=14,
            token_hash="replacement-hash",
        )

    async def get_session_by_token_hash(
        self,
        token_hash: str,
        *,
        lock_for_update: bool = False,
    ) -> SimpleNamespace | None:
        self.calls.append(
            (
                "get_session_by_token_hash",
                (token_hash, lock_for_update),
            )
        )
        return self.current_session

    async def create_session(
        self,
        payload: dict[str, Any],
    ) -> SimpleNamespace:
        self.calls.append(("create_session", payload))
        return self.replacement_session

    async def rotate_session(
        self,
        session_id: int,
        payload: dict[str, Any],
    ) -> SimpleNamespace:
        self.calls.append(("rotate_session", (session_id, payload)))
        return self.replacement_session

    async def revoke_session(self, session_id: int) -> SimpleNamespace:
        self.calls.append(("revoke_session", session_id))
        source = self.current_session or self.replacement_session
        source.revoked_at = NOW
        return source

    async def revoke_user_sessions(self, user_id: int) -> int:
        self.calls.append(("revoke_user_sessions", user_id))
        return 2

    async def revoke_family(self, family_id: str) -> int:
        self.calls.append(("revoke_family", family_id))
        return 2


class FakePasswordResetStore:
    """Configurable password-reset store replacement."""

    def __init__(self, session: object) -> None:
        self.session = session
        self.calls: list[tuple[str, object]] = []
        self.token: SimpleNamespace | None = _password_reset_token_model()
        self.consume_error: Exception | None = None

    async def create_token(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                "create_token",
                {
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at,
                },
            )
        )
        self.token = _password_reset_token_model(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return self.token

    async def get_token_by_hash(
        self,
        *,
        token_hash: str,
    ) -> SimpleNamespace | None:
        self.calls.append(("get_token_by_hash", token_hash))
        return self.token

    async def consume_token(
        self,
        *,
        token_hash: str,
        consumed_at: datetime,
    ) -> SimpleNamespace:
        self.calls.append(
            ("consume_token", (token_hash, consumed_at))
        )

        if self.consume_error is not None:
            raise self.consume_error

        assert self.token is not None
        self.token.used_at = consumed_at
        return self.token

    async def revoke_pending_tokens_for_user(
        self,
        *,
        user_id: int,
        revoked_at: datetime,
    ) -> int:
        self.calls.append(
            ("revoke_pending_tokens_for_user", (user_id, revoked_at))
        )
        return 2

    async def delete_expired_tokens(self, *, before: datetime) -> int:
        self.calls.append(("delete_expired_tokens", before))
        return 3


class StoreHarness:
    """Install fake transaction scopes and concrete persistence stores."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.events: list[tuple[str, object]] = []
        self.read_session = object()
        self.write_session = object()
        self.session_factory = cast(SessionFactory, object())
        self.user_stores: dict[object, FakeUserStore] = {}
        self.session_stores: dict[object, FakeAuthSessionStore] = {}
        self.password_reset_stores: dict[
            object,
            FakePasswordResetStore,
        ] = {}

        @asynccontextmanager
        async def read_scope(
            session_factory: SessionFactory,
        ) -> AsyncIterator[object]:
            self.events.append(("read_enter", session_factory))
            try:
                yield self.read_session
            finally:
                self.events.append(("read_exit", self.read_session))

        @asynccontextmanager
        async def transaction_scope(
            session_factory: SessionFactory,
        ) -> AsyncIterator[object]:
            self.events.append(("write_enter", session_factory))
            try:
                yield self.write_session
            finally:
                self.events.append(("write_exit", self.write_session))

        def user_store_factory(session: object) -> FakeUserStore:
            return self.user_stores.setdefault(session, FakeUserStore(session))

        def session_store_factory(session: object) -> FakeAuthSessionStore:
            return self.session_stores.setdefault(
                session,
                FakeAuthSessionStore(session),
            )

        def password_reset_store_factory(
            session: object,
        ) -> FakePasswordResetStore:
            return self.password_reset_stores.setdefault(
                session,
                FakePasswordResetStore(session),
            )

        monkeypatch.setattr(transactional_store, "async_session_scope", read_scope)
        monkeypatch.setattr(
            transactional_store,
            "async_transaction_scope",
            transaction_scope,
        )
        monkeypatch.setattr(
            transactional_store,
            "SQLAlchemyUserStore",
            user_store_factory,
        )
        monkeypatch.setattr(
            transactional_store,
            "SQLAlchemyAuthSessionStore",
            session_store_factory,
        )
        monkeypatch.setattr(
            transactional_store,
            "SQLAlchemyPasswordResetStore",
            password_reset_store_factory,
        )

    @property
    def read_user_store(self) -> FakeUserStore:
        return self.user_stores.setdefault(
            self.read_session,
            FakeUserStore(self.read_session),
        )

    @property
    def write_user_store(self) -> FakeUserStore:
        return self.user_stores.setdefault(
            self.write_session,
            FakeUserStore(self.write_session),
        )

    @property
    def read_session_store(self) -> FakeAuthSessionStore:
        return self.session_stores.setdefault(
            self.read_session,
            FakeAuthSessionStore(self.read_session),
        )

    @property
    def write_session_store(self) -> FakeAuthSessionStore:
        return self.session_stores.setdefault(
            self.write_session,
            FakeAuthSessionStore(self.write_session),
        )

    @property
    def read_password_reset_store(self) -> FakePasswordResetStore:
        return self.password_reset_stores.setdefault(
            self.read_session,
            FakePasswordResetStore(self.read_session),
        )

    @property
    def write_password_reset_store(self) -> FakePasswordResetStore:
        return self.password_reset_stores.setdefault(
            self.write_session,
            FakePasswordResetStore(self.write_session),
        )

    def auth_store(self) -> AuthStore:
        return AuthStore(self.session_factory)


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> StoreHarness:
    return StoreHarness(monkeypatch)


def test_auth_user_record_exposes_verified_and_disabled_properties() -> None:
    """Derive account state from persisted timestamps."""

    active = AuthUserRecord(
        user_id=7,
        email="user@example.com",
        password_hash="hash",
        name=None,
        avatar_url=None,
        auth_provider="password",
        google_subject=None,
        email_verified_at=NOW,
        disabled_at=None,
    )
    disabled = AuthUserRecord(
        user_id=8,
        email="disabled@example.com",
        password_hash=None,
        name=None,
        avatar_url=None,
        auth_provider="google",
        google_subject="subject",
        email_verified_at=None,
        disabled_at=NOW,
    )

    assert active.email_verified is True
    assert active.disabled is False
    assert disabled.email_verified is False
    assert disabled.disabled is True


def test_auth_session_record_exposes_revoked_property() -> None:
    """Derive revocation state from the persisted timestamp."""

    active = transactional_store._auth_session_record(_session_model())
    revoked = transactional_store._auth_session_record(
        _session_model(revoked_at=NOW)
    )

    assert active.revoked is False
    assert revoked.revoked is True


def test_password_reset_record_hides_hash_and_exposes_used_property() -> None:
    """Keep token hashes out of repr output and derive consumption state."""

    pending = transactional_store._password_reset_token_record(
        _password_reset_token_model()
    )
    used = transactional_store._password_reset_token_record(
        _password_reset_token_model(used_at=NOW)
    )

    assert isinstance(pending, PasswordResetTokenRecord)
    assert pending.used is False
    assert used.used is True
    assert "password-reset-token-hash" not in repr(pending)


def test_get_user_uses_short_read_session_and_returns_detached_record(
    harness: StoreHarness,
) -> None:
    """Close the read session before returning immutable user data."""

    result = _run(harness.auth_store().get_user(7))

    assert isinstance(result, AuthUserRecord)
    assert result.user_id == 7
    assert harness.read_user_store.calls == [("get_user", 7)]
    assert harness.events == [
        ("read_enter", harness.session_factory),
        ("read_exit", harness.read_session),
    ]


def test_get_user_by_email_uses_short_read_session(
    harness: StoreHarness,
) -> None:
    """Read by email without leaking an open SQLAlchemy session."""

    result = _run(harness.auth_store().get_user_by_email("user@example.com"))

    assert isinstance(result, AuthUserRecord)
    assert harness.read_user_store.calls == [
        ("get_user_by_email", "user@example.com")
    ]
    assert harness.events[-1] == ("read_exit", harness.read_session)


def test_get_user_by_google_subject_uses_short_read_session(
    harness: StoreHarness,
) -> None:
    """Read a Google-linked account within one short session."""

    result = _run(
        harness.auth_store().get_user_by_google_sub("google-subject")
    )

    assert isinstance(result, AuthUserRecord)
    assert harness.read_user_store.calls == [
        ("get_user_by_google_sub", "google-subject")
    ]
    assert harness.events[-1] == ("read_exit", harness.read_session)


def test_get_session_by_token_hash_uses_short_read_session(
    harness: StoreHarness,
) -> None:
    """Return detached refresh metadata after closing the read session."""

    result = _run(
        harness.auth_store().get_session_by_token_hash("token-hash")
    )

    assert isinstance(result, AuthSessionRecord)
    assert harness.read_session_store.calls == [
        ("get_session_by_token_hash", ("token-hash", False))
    ]
    assert harness.events[-1] == ("read_exit", harness.read_session)


def test_create_password_reset_token_replaces_pending_tokens_atomically(
    harness: StoreHarness,
) -> None:
    """Revoke pending tokens and create the replacement in one transaction."""

    result = _run(
        harness.auth_store().create_password_reset_token(
            user_id=7,
            token_hash="replacement-reset-hash",
            expires_at=NOW + timedelta(minutes=30),
            requested_at=NOW,
        )
    )

    assert isinstance(result, PasswordResetTokenRecord)
    assert result.token_hash == "replacement-reset-hash"
    assert harness.write_password_reset_store.calls == [
        ("revoke_pending_tokens_for_user", (7, NOW)),
        (
            "create_token",
            {
                "user_id": 7,
                "token_hash": "replacement-reset-hash",
                "expires_at": NOW + timedelta(minutes=30),
            },
        ),
    ]
    assert harness.events == [
        ("write_enter", harness.session_factory),
        ("write_exit", harness.write_session),
    ]


def test_get_password_reset_token_uses_short_read_session(
    harness: StoreHarness,
) -> None:
    """Return a detached reset-token snapshot after closing the session."""

    result = _run(
        harness.auth_store().get_password_reset_token_by_hash(
            "password-reset-token-hash"
        )
    )

    assert isinstance(result, PasswordResetTokenRecord)
    assert harness.read_password_reset_store.calls == [
        ("get_token_by_hash", "password-reset-token-hash")
    ]
    assert harness.events[-1] == ("read_exit", harness.read_session)


def test_reset_password_consumes_token_and_revokes_sessions_atomically(
    harness: StoreHarness,
) -> None:
    """Run every password-reset write through one transaction and session."""

    result = _run(
        harness.auth_store().reset_password_with_token(
            token_hash="password-reset-token-hash",
            password_hash="new-argon2-hash",
            consumed_at=NOW,
        )
    )

    assert result.password_hash == "new-argon2-hash"
    assert harness.write_password_reset_store.calls == [
        ("consume_token", ("password-reset-token-hash", NOW))
    ]
    assert harness.write_user_store.calls == [
        ("update_password_hash", (7, "new-argon2-hash"))
    ]
    assert harness.write_session_store.calls == [
        ("revoke_user_sessions", 7)
    ]
    assert (
        harness.write_password_reset_store.session
        is harness.write_user_store.session
        is harness.write_session_store.session
    )
    assert harness.events == [
        ("write_enter", harness.session_factory),
        ("write_exit", harness.write_session),
    ]


def test_reset_password_stops_when_token_cannot_be_consumed(
    harness: StoreHarness,
) -> None:
    """Do not update credentials or sessions after token rejection."""

    harness.write_password_reset_store.consume_error = StoreError(
        technical_message="Reset token cannot be consumed.",
    )

    with pytest.raises(StoreError):
        _run(
            harness.auth_store().reset_password_with_token(
                token_hash="invalid-reset-token-hash",
                password_hash="new-argon2-hash",
                consumed_at=NOW,
            )
        )

    assert harness.write_user_store.calls == []
    assert harness.write_session_store.calls == []


def test_delete_expired_password_reset_tokens_uses_write_transaction(
    harness: StoreHarness,
) -> None:
    """Commit bounded password-reset token cleanup before returning."""

    result = _run(
        harness.auth_store().delete_expired_password_reset_tokens(before=NOW)
    )

    assert result == 3
    assert harness.write_password_reset_store.calls == [
        ("delete_expired_tokens", NOW)
    ]
    assert harness.events[-1] == ("write_exit", harness.write_session)


def test_create_password_user_with_session_commits_user_and_session_together(
    harness: StoreHarness,
) -> None:
    """Create a local user and initial refresh session in one transaction."""

    result = _run(
        harness.auth_store().create_password_user_with_session(
            email="user@example.com",
            password_hash="argon2-hash",
            name="Ada",
            token_hash="token-hash",
            family_id="family-id",
            session_expires_at=NOW + timedelta(days=30),
        )
    )

    user_payload = harness.write_user_store.calls[0][1]
    session_payload = harness.write_session_store.calls[0][1]
    assert isinstance(user_payload, dict)
    assert user_payload["password_hash"] == "argon2-hash"
    assert isinstance(session_payload, dict)
    assert session_payload["user_id"] == result.user.user_id
    assert harness.write_user_store.session is harness.write_session_store.session
    assert harness.events == [
        ("write_enter", harness.session_factory),
        ("write_exit", harness.write_session),
    ]


def test_create_google_user_with_session_commits_user_and_session_together(
    harness: StoreHarness,
) -> None:
    """Create a Google user and initial session atomically."""

    _run(
        harness.auth_store().create_google_user_with_session(
            email="user@example.com",
            google_subject="google-subject",
            email_verified_at=NOW,
            name="Ada",
            avatar_url="https://example.com/avatar.png",
            token_hash="token-hash",
            family_id="family-id",
            session_expires_at=NOW + timedelta(days=30),
        )
    )

    user_payload = harness.write_user_store.calls[0][1]
    assert isinstance(user_payload, dict)
    assert user_payload["auth_provider"] == "google"
    assert user_payload["google_sub"] == "google-subject"
    assert harness.write_user_store.session is harness.write_session_store.session
    assert harness.events[0][0] == "write_enter"
    assert harness.events[-1][0] == "write_exit"


def test_create_session_uses_short_write_transaction(
    harness: StoreHarness,
) -> None:
    """Commit an independent refresh session before returning."""

    result = _run(
        harness.auth_store().create_session(
            user_id=7,
            token_hash="new-token-hash",
            family_id="family-id",
            expires_at=NOW + timedelta(days=30),
        )
    )

    assert isinstance(result, AuthSessionRecord)
    assert harness.write_session_store.calls[0][0] == "create_session"
    assert harness.events[-1] == ("write_exit", harness.write_session)


def test_rotate_session_uses_single_write_transaction(
    harness: StoreHarness,
) -> None:
    """Revoke and replace a session within one transaction boundary."""

    result = _run(
        harness.auth_store().rotate_session(
            current_session_id=13,
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
        )
    )

    assert result.session_id == 14
    assert harness.write_session_store.calls[0][0] == "rotate_session"
    assert [event[0] for event in harness.events] == [
        "write_enter",
        "write_exit",
    ]


def test_rotate_session_by_token_hash_returns_not_found(
    harness: StoreHarness,
) -> None:
    """Return a controlled result when no refresh digest exists."""

    harness.write_session_store.current_session = None

    result = _run(
        harness.auth_store().rotate_session_by_token_hash(
            current_token_hash="unknown-hash",
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
            checked_at=NOW,
        )
    )

    assert result.status == "not_found"
    assert result.current_session is None


def test_rotate_session_by_token_hash_returns_expired(
    harness: StoreHarness,
) -> None:
    """Revoke an expired refresh session without creating a replacement."""

    harness.write_session_store.current_session = _session_model(
        expires_at=NOW - timedelta(seconds=1)
    )

    result = _run(
        harness.auth_store().rotate_session_by_token_hash(
            current_token_hash="expired-hash",
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
            checked_at=NOW,
        )
    )

    assert result.status == "expired"
    assert ("revoke_session", 13) in harness.write_session_store.calls
    assert not any(
        call[0] == "rotate_session"
        for call in harness.write_session_store.calls
    )


def test_rotate_session_by_token_hash_returns_user_not_found(
    harness: StoreHarness,
) -> None:
    """Revoke an orphaned refresh session instead of rotating it."""

    harness.write_user_store.user = None

    result = _run(
        harness.auth_store().rotate_session_by_token_hash(
            current_token_hash="token-hash",
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
            checked_at=NOW,
        )
    )

    assert result.status == "user_not_found"
    assert ("revoke_session", 13) in harness.write_session_store.calls


def test_rotate_session_by_token_hash_rotates_active_session_atomically(
    harness: StoreHarness,
) -> None:
    """Lock, validate, and replace an active session in one transaction."""

    result = _run(
        harness.auth_store().rotate_session_by_token_hash(
            current_token_hash="token-hash",
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
            checked_at=NOW,
        )
    )

    assert result.status == "rotated"
    assert result.user is not None
    assert result.current_session is not None
    assert result.replacement_session is not None
    assert harness.write_session_store.calls[0] == (
        "get_session_by_token_hash",
        ("token-hash", True),
    )
    assert harness.write_session_store.calls[-1][0] == "rotate_session"
    assert [event[0] for event in harness.events] == [
        "write_enter",
        "write_exit",
    ]


def test_rotate_session_by_token_hash_revokes_family_on_reuse(
    harness: StoreHarness,
) -> None:
    """Revoke the active family when an old refresh token is reused."""

    harness.write_session_store.current_session = _session_model(
        revoked_at=NOW,
        replaced_by_session_id=14,
    )

    result = _run(
        harness.auth_store().rotate_session_by_token_hash(
            current_token_hash="reused-hash",
            replacement_token_hash="replacement-hash",
            replacement_expires_at=NOW + timedelta(days=30),
            checked_at=NOW,
        )
    )

    assert result.status == "reused"
    assert ("revoke_family", "family-id") in harness.write_session_store.calls


def test_revoke_session_uses_short_write_transaction(
    harness: StoreHarness,
) -> None:
    """Commit individual session revocation before returning."""

    result = _run(harness.auth_store().revoke_session(13))

    assert result.revoked is True
    assert harness.write_session_store.calls == [("revoke_session", 13)]
    assert harness.events[-1][0] == "write_exit"


def test_revoke_user_sessions_uses_short_write_transaction(
    harness: StoreHarness,
) -> None:
    """Commit bulk user-session revocation in one transaction."""

    count = _run(harness.auth_store().revoke_user_sessions(7))

    assert count == 2
    assert harness.write_session_store.calls == [
        ("revoke_user_sessions", 7)
    ]
    assert harness.events[-1][0] == "write_exit"


def test_revoke_session_family_uses_short_write_transaction(
    harness: StoreHarness,
) -> None:
    """Commit refresh-family revocation in one transaction."""

    count = _run(harness.auth_store().revoke_session_family("family-id"))

    assert count == 2
    assert harness.write_session_store.calls == [
        ("revoke_family", "family-id")
    ]
    assert harness.events[-1][0] == "write_exit"


def test_update_password_hash_uses_short_write_transaction(
    harness: StoreHarness,
) -> None:
    """Persist an upgraded password hash through a committed short write."""

    result = _run(
        harness.auth_store().update_password_hash(7, "replacement-hash")
    )

    assert result.password_hash == "replacement-hash"
    assert harness.write_user_store.calls == [
        ("update_password_hash", (7, "replacement-hash"))
    ]
    assert harness.events[-1][0] == "write_exit"


@pytest.mark.parametrize("user_id", [0, -1, True, 1.5, "7"])
def test_invalid_identifiers_raise_user_store_error(
    harness: StoreHarness,
    user_id: object,
) -> None:
    """Reject invalid identifiers before opening a database session."""

    with pytest.raises(UserStoreError):
        _run(harness.auth_store().get_user(user_id))  # type: ignore[arg-type]

    assert harness.events == []
