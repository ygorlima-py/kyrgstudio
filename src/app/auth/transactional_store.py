"""Short-lived transactional persistence boundary for authentication.

SQLAlchemy stores execute database statements but intentionally do not own
commit or rollback. ``AuthStore`` composes those stores with application-level
transaction boundaries so authentication never leaks an open session and does
not keep database resources allocated during password hashing, Google token
verification, or JWT work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.errors import UserStoreError
from app.store.database import (
    SessionFactory,
    async_session_scope,
    async_transaction_scope,
)
from app.store.email_verifications import SQLAlchemyEmailVerificationStore
from app.store.models import AuthSession, EmailVerificationToken, User
from app.store.users import (
    DEFAULT_AUTH_PROVIDER,
    GOOGLE_AUTH_PROVIDER,
    SQLAlchemyAuthSessionStore,
    SQLAlchemyUserStore,
)


RefreshSessionRotationStatus = Literal[
    "rotated",
    "not_found",
    "expired",
    "reused",
    "user_not_found",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthUserRecord:
    """Session-independent user data required by authentication use cases.

    ``password_hash`` is available only so the authentication service can
    verify local credentials. Marking it ``repr=False`` prevents accidental
    disclosure in ordinary object representations and trace output.
    """

    user_id: int
    email: str
    password_hash: str | None = field(repr=False)
    name: str | None
    avatar_url: str | None
    auth_provider: str
    google_subject: str | None
    email_verified_at: datetime | None
    disabled_at: datetime | None

    @property
    def email_verified(self) -> bool:
        """Return whether the user has a persisted verification timestamp."""

        return self.email_verified_at is not None

    @property
    def disabled(self) -> bool:
        """Return whether the account has been administratively disabled."""

        return self.disabled_at is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthSessionRecord:
    """Session-independent snapshot of one persisted refresh-token session."""

    session_id: int
    user_id: int
    token_hash: str = field(repr=False)
    family_id: str
    expires_at: datetime
    last_used_at: datetime
    revoked_at: datetime | None
    replaced_by_session_id: int | None
    created_at: datetime

    @property
    def revoked(self) -> bool:
        """Return whether this refresh session can no longer be used."""

        return self.revoked_at is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class EmailVerificationTokenRecord:
    """Session-independent snapshot of one email verification token."""

    token_id: int
    user_id: int
    token_hash: str = field(repr=False)
    email: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    @property
    def used(self) -> bool:
        """Return whether this verification link was already consumed."""

        return self.used_at is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthUserSessionRecord:
    """User and initial refresh session committed in one transaction."""

    user: AuthUserRecord
    session: AuthSessionRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class RefreshSessionRotationRecord:
    """Outcome of one atomic refresh-session rotation attempt."""

    status: RefreshSessionRotationStatus
    user: AuthUserRecord | None = None
    current_session: AuthSessionRecord | None = None
    replacement_session: AuthSessionRecord | None = None


class AuthStore:
    """Persist authentication state through short, explicit transactions.

    Read methods open a session only for the duration of one query. Write
    methods commit before returning. Returned values are immutable snapshots,
    not SQLAlchemy models, so callers cannot accidentally trigger lazy database
    access after the session has closed.
    """

    __slots__ = ("session_factory",)

    def __init__(self, session_factory: SessionFactory) -> None:
        """Create the adapter from the application's async session factory."""

        self.session_factory = session_factory

    async def get_user(self, user_id: int) -> AuthUserRecord | None:
        """Load one user in a short-lived read session."""

        normalized_user_id = _positive_identifier(user_id, field_name="user_id")

        async with async_session_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).get_user(
                normalized_user_id
            )
            user_record = _optional_user_record(user)

        return user_record

    async def get_user_by_email(self, email: str) -> AuthUserRecord | None:
        """Load one user by normalized email in a short-lived session."""

        async with async_session_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).get_user_by_email(email)
            user_record = _optional_user_record(user)

        return user_record

    async def get_user_by_google_sub(
        self,
        subject: str,
    ) -> AuthUserRecord | None:
        """Load one user by the verified Google subject identifier."""

        async with async_session_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(
                session
            ).get_user_by_google_sub(subject)
            user_record = _optional_user_record(user)

        return user_record

    async def get_session_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthSessionRecord | None:
        """Load refresh-session metadata by its deterministic token digest."""

        async with async_session_scope(self.session_factory) as session:
            auth_session = await SQLAlchemyAuthSessionStore(
                session
            ).get_session_by_token_hash(token_hash)
            session_record = _optional_auth_session_record(auth_session)

        return session_record

    async def create_email_verification_token(
        self,
        *,
        user_id: int,
        email: str,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationTokenRecord:
        """Create and commit one email verification token hash."""

        normalized_user_id = _positive_identifier(
            user_id,
            field_name="user_id",
        )
        normalized_expires_at = _utc_datetime(
            expires_at,
            field_name="expires_at",
        )

        async with async_transaction_scope(self.session_factory) as session:
            token = await SQLAlchemyEmailVerificationStore(
                session
            ).create_token(
                user_id=normalized_user_id,
                email=email,
                token_hash=token_hash,
                expires_at=normalized_expires_at,
            )
            token_record = _email_verification_token_record(token)

        return token_record

    async def get_email_verification_token_by_hash(
        self,
        token_hash: str,
    ) -> EmailVerificationTokenRecord | None:
        """Load one email verification token by its deterministic digest."""

        async with async_session_scope(self.session_factory) as session:
            token = await SQLAlchemyEmailVerificationStore(
                session
            ).get_token_by_hash(token_hash)
            token_record = _optional_email_verification_token_record(token)

        return token_record

    async def mark_email_verification_token_used(
        self,
        token_id: int,
    ) -> EmailVerificationTokenRecord:
        """Mark one email verification token as used and commit it."""

        normalized_token_id = _positive_identifier(
            token_id,
            field_name="token_id",
        )

        async with async_transaction_scope(self.session_factory) as session:
            token = await SQLAlchemyEmailVerificationStore(
                session
            ).mark_token_used(normalized_token_id)
            token_record = _email_verification_token_record(token)

        return token_record

    async def revoke_pending_email_verification_tokens_for_user(
        self,
        user_id: int,
    ) -> int:
        """Mark pending verification tokens for one user as unusable."""

        normalized_user_id = _positive_identifier(
            user_id,
            field_name="user_id",
        )

        async with async_transaction_scope(self.session_factory) as session:
            revoked_token_count = await SQLAlchemyEmailVerificationStore(
                session
            ).revoke_pending_tokens_for_user(normalized_user_id)

        return revoked_token_count

    async def create_password_user(
        self,
        *,
        email: str,
        password_hash: str,
        name: str,
    ) -> AuthUserRecord:
        """Create an unverified password user without opening a session."""

        user_payload = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "auth_provider": DEFAULT_AUTH_PROVIDER,
            "email_verified_at": None,
        }

        async with async_transaction_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).create_user(user_payload)
            user_record = _user_record(user)

        return user_record

    async def mark_user_email_verified(
        self,
        user_id: int,
    ) -> AuthUserRecord:
        """Mark one user's email as verified and commit the change."""

        normalized_user_id = _positive_identifier(
            user_id,
            field_name="user_id",
        )

        async with async_transaction_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).mark_email_verified(
                normalized_user_id
            )
            user_record = _user_record(user)

        return user_record

    async def create_password_user_with_session(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None,
        token_hash: str,
        family_id: str,
        session_expires_at: datetime,
        email_verified_at: datetime | None = None,
    ) -> AuthUserSessionRecord:
        """Atomically create a password user and initial refresh session.

        The method accepts an Argon2id hash, never a plain password. If either
        insert fails, the outer transaction rolls both records back.
        """

        user_payload = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "auth_provider": DEFAULT_AUTH_PROVIDER,
            "email_verified_at": email_verified_at,
        }

        user_with_session = await self._create_user_with_session(
            user_payload=user_payload,
            token_hash=token_hash,
            family_id=family_id,
            session_expires_at=session_expires_at,
        )
        return user_with_session

    async def create_google_user_with_session(
        self,
        *,
        email: str,
        google_subject: str,
        email_verified_at: datetime | None,
        name: str | None,
        avatar_url: str | None,
        token_hash: str,
        family_id: str,
        session_expires_at: datetime,
    ) -> AuthUserSessionRecord:
        """Atomically create a verified Google user and refresh session.

        This method persists only identity data already verified by the Google
        token verifier. Existing local accounts are not linked or overwritten;
        database uniqueness conflicts remain visible to ``AuthService``.
        """

        user_payload = {
            "email": email,
            "password_hash": None,
            "name": name,
            "avatar_url": avatar_url,
            "auth_provider": GOOGLE_AUTH_PROVIDER,
            "google_sub": google_subject,
            "email_verified_at": email_verified_at,
        }

        user_with_session = await self._create_user_with_session(
            user_payload=user_payload,
            token_hash=token_hash,
            family_id=family_id,
            session_expires_at=session_expires_at,
        )
        return user_with_session

    async def create_session(
        self,
        *,
        user_id: int,
        token_hash: str,
        family_id: str,
        expires_at: datetime,
    ) -> AuthSessionRecord:
        """Create and commit a refresh session for an existing user."""

        session_payload = _auth_session_payload(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )

        async with async_transaction_scope(self.session_factory) as session:
            auth_session = await SQLAlchemyAuthSessionStore(
                session
            ).create_session(session_payload)
            session_record = _auth_session_record(auth_session)

        return session_record

    async def rotate_session(
        self,
        *,
        current_session_id: int,
        replacement_token_hash: str,
        replacement_expires_at: datetime,
    ) -> AuthSessionRecord:
        """Atomically revoke one refresh session and create its replacement.

        The concrete session store locks the current row and updates both
        records in the same transaction. Concurrent rotation attempts cannot
        both succeed.
        """

        replacement_payload = {
            "token_hash": replacement_token_hash,
            "expires_at": replacement_expires_at,
        }

        async with async_transaction_scope(self.session_factory) as session:
            replacement_session = await SQLAlchemyAuthSessionStore(
                session
            ).rotate_session(
                current_session_id,
                replacement_payload,
            )
            session_record = _auth_session_record(replacement_session)

        return session_record

    async def rotate_session_by_token_hash(
        self,
        *,
        current_token_hash: str,
        replacement_token_hash: str,
        replacement_expires_at: datetime,
        checked_at: datetime,
    ) -> RefreshSessionRotationRecord:
        """Validate and rotate a refresh session in one locked transaction.

        The current row is selected with ``FOR UPDATE`` before its state is
        inspected. A reused token revokes its active family in the same
        transaction, while an expired token is revoked without creating a
        replacement.
        """

        normalized_checked_at = _utc_datetime(
            checked_at,
            field_name="checked_at",
        )
        replacement_payload = {
            "token_hash": replacement_token_hash,
            "expires_at": replacement_expires_at,
        }

        async with async_transaction_scope(self.session_factory) as session:
            user_store = SQLAlchemyUserStore(session)
            session_store = SQLAlchemyAuthSessionStore(session)
            current_session = await session_store.get_session_by_token_hash(
                current_token_hash,
                lock_for_update=True,
            )

            if current_session is None:
                rotation_result = RefreshSessionRotationRecord(
                    status="not_found",
                )
            elif (
                current_session.revoked_at is not None
                or current_session.replaced_by_session_id is not None
            ):
                await session_store.revoke_family(current_session.family_id)
                rotation_result = RefreshSessionRotationRecord(
                    status="reused",
                    current_session=_auth_session_record(current_session),
                )
            elif _utc_datetime(
                current_session.expires_at,
                field_name="expires_at",
            ) <= normalized_checked_at:
                revoked_session = await session_store.revoke_session(
                    current_session.id
                )
                rotation_result = RefreshSessionRotationRecord(
                    status="expired",
                    current_session=_auth_session_record(revoked_session),
                )
            else:
                user = await user_store.get_user(current_session.user_id)

                if user is None:
                    revoked_session = await session_store.revoke_session(
                        current_session.id
                    )
                    rotation_result = RefreshSessionRotationRecord(
                        status="user_not_found",
                        current_session=_auth_session_record(revoked_session),
                    )
                else:
                    replacement_session = await session_store.rotate_session(
                        current_session.id,
                        replacement_payload,
                    )
                    rotation_result = RefreshSessionRotationRecord(
                        status="rotated",
                        user=_user_record(user),
                        current_session=_auth_session_record(current_session),
                        replacement_session=_auth_session_record(
                            replacement_session
                        ),
                    )

        return rotation_result

    async def revoke_session(
        self,
        session_id: int,
    ) -> AuthSessionRecord:
        """Revoke and commit one refresh session idempotently."""

        async with async_transaction_scope(self.session_factory) as session:
            auth_session = await SQLAlchemyAuthSessionStore(
                session
            ).revoke_session(session_id)
            session_record = _auth_session_record(auth_session)

        return session_record

    async def revoke_user_sessions(self, user_id: int) -> int:
        """Revoke and commit every active refresh session for one user."""

        async with async_transaction_scope(self.session_factory) as session:
            revoked_session_count = await SQLAlchemyAuthSessionStore(
                session
            ).revoke_user_sessions(user_id)

        return revoked_session_count

    async def revoke_session_family(self, family_id: str) -> int:
        """Revoke one refresh-token family after reuse is detected."""

        async with async_transaction_scope(self.session_factory) as session:
            revoked_session_count = await SQLAlchemyAuthSessionStore(
                session
            ).revoke_family(family_id)

        return revoked_session_count

    async def update_password_hash(
        self,
        user_id: int,
        password_hash: str,
    ) -> AuthUserRecord:
        """Persist an already-generated replacement password hash."""

        async with async_transaction_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).update_password_hash(
                user_id,
                password_hash,
            )
            user_record = _user_record(user)

        return user_record

    async def _create_user_with_session(
        self,
        *,
        user_payload: dict[str, Any],
        token_hash: str,
        family_id: str,
        session_expires_at: datetime,
    ) -> AuthUserSessionRecord:
        """Create related user and session records in one transaction."""

        async with async_transaction_scope(self.session_factory) as session:
            user = await SQLAlchemyUserStore(session).create_user(user_payload)
            auth_session = await SQLAlchemyAuthSessionStore(
                session
            ).create_session(
                _auth_session_payload(
                    user_id=user.id,
                    token_hash=token_hash,
                    family_id=family_id,
                    expires_at=session_expires_at,
                )
            )
            user_with_session = AuthUserSessionRecord(
                user=_user_record(user),
                session=_auth_session_record(auth_session),
            )

        return user_with_session


def _auth_session_payload(
    *,
    user_id: int,
    token_hash: str,
    family_id: str,
    expires_at: datetime,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "token_hash": token_hash,
        "family_id": family_id,
        "expires_at": expires_at,
    }


def _optional_user_record(user: User | None) -> AuthUserRecord | None:
    return None if user is None else _user_record(user)


def _user_record(user: User) -> AuthUserRecord:
    return AuthUserRecord(
        user_id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        name=user.name,
        avatar_url=user.avatar_url,
        auth_provider=user.auth_provider,
        google_subject=user.google_sub,
        email_verified_at=user.email_verified_at,
        disabled_at=user.disabled_at,
    )


def _optional_auth_session_record(
    auth_session: AuthSession | None,
) -> AuthSessionRecord | None:
    if auth_session is None:
        return None

    return _auth_session_record(auth_session)


def _optional_email_verification_token_record(
    token: EmailVerificationToken | None,
) -> EmailVerificationTokenRecord | None:
    if token is None:
        return None

    return _email_verification_token_record(token)


def _email_verification_token_record(
    token: EmailVerificationToken,
) -> EmailVerificationTokenRecord:
    return EmailVerificationTokenRecord(
        token_id=token.id,
        user_id=token.user_id,
        token_hash=token.token_hash,
        email=token.email,
        expires_at=token.expires_at,
        used_at=token.used_at,
        created_at=token.created_at,
    )


def _auth_session_record(auth_session: AuthSession) -> AuthSessionRecord:
    return AuthSessionRecord(
        session_id=auth_session.id,
        user_id=auth_session.user_id,
        token_hash=auth_session.token_hash,
        family_id=auth_session.family_id,
        expires_at=auth_session.expires_at,
        last_used_at=auth_session.last_used_at,
        revoked_at=auth_session.revoked_at,
        replaced_by_session_id=auth_session.replaced_by_session_id,
        created_at=auth_session.created_at,
    )


def _positive_identifier(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise UserStoreError(
            technical_message=f"{field_name} must be a positive integer.",
            details={"field": field_name},
        )

    return value


def _utc_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise UserStoreError(
            technical_message=f"{field_name} must be a datetime.",
            details={"field": field_name},
        )

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


__all__ = [
    "AuthSessionRecord",
    "AuthStore",
    "AuthUserRecord",
    "AuthUserSessionRecord",
    "EmailVerificationTokenRecord",
    "RefreshSessionRotationRecord",
]
