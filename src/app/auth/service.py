"""Authentication use cases independent from HTTP and FastAPI.

``AuthService`` coordinates verified credentials, short-lived transactional
persistence, and application-owned tokens. It never returns SQLAlchemy models,
opens HTTP responses, reads environment settings, or stores plain passwords and
refresh tokens.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import PasswordHasher
from app.auth.principal import AuthenticatedPrincipal, IssuedAuthTokens
from app.auth.tokens import AccessTokenService, RefreshTokenGenerator
from app.auth.transactional_store import (
    AuthStore,
    AuthUserRecord,
)
from app.errors import (
    AccountDisabledError,
    AccountLinkRequiredError,
    AuthConfigurationError,
    EmailVerificationRequiredError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidTokenError,
    RefreshTokenInvalidError,
    UserStoreError,
)


MAXIMUM_AUTH_EMAIL_LENGTH = 320
MAXIMUM_AUTH_NAME_LENGTH = 255


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticationResult:
    """Verified principal and credentials produced by authentication."""

    principal: AuthenticatedPrincipal
    tokens: IssuedAuthTokens


@dataclass(frozen=True, slots=True, kw_only=True)
class _RefreshTokenMaterial:
    """Plain refresh token and derived metadata used during one operation."""

    token: str = field(repr=False)
    token_hash: str = field(repr=False)
    expires_at: datetime


class AuthService:
    """Coordinate registration, login, refresh, logout, and authentication.

    All dependencies and configuration are supplied at construction time. The
    service keeps no user or session state in memory; persisted authentication
    state always comes from ``AuthStore``.
    """

    __slots__ = (
        "_clock",
        "access_token_service",
        "auth_store",
        "google_token_verifier",
        "password_hasher",
        "refresh_token_generator",
        "refresh_token_ttl_seconds",
    )

    def __init__(
        self,
        *,
        auth_store: AuthStore,
        password_hasher: PasswordHasher,
        access_token_service: AccessTokenService,
        refresh_token_generator: RefreshTokenGenerator,
        google_token_verifier: GoogleTokenVerifier | None,
        refresh_token_ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Create the service from ready-to-use application dependencies."""

        self.auth_store = auth_store
        self.password_hasher = password_hasher
        self.access_token_service = access_token_service
        self.refresh_token_generator = refresh_token_generator
        self.google_token_verifier = google_token_verifier
        self.refresh_token_ttl_seconds = _positive_integer(
            refresh_token_ttl_seconds,
            field_name="refresh_token_ttl_seconds",
        )
        self._clock = clock if clock is not None else _utc_now

        if (
            self.refresh_token_ttl_seconds
            <= self.access_token_service.ttl_seconds
        ):
            raise AuthConfigurationError(
                technical_message=(
                    "Refresh token TTL must be greater than access token TTL."
                ),
            )

    async def register_with_password(
        self,
        *,
        email: str,
        password: str,
        name: str | None = None,
    ) -> AuthenticationResult:
        """Register a password user and issue the initial token pair.

        Password hashing happens before the database transaction. The store
        receives only the Argon2id hash and creates the user and refresh session
        atomically.
        """

        normalized_email = _registration_email(email)
        normalized_name = _optional_name(name)
        password_hash = _password_hash_for_registration(
            self.password_hasher,
            password,
        )
        issued_at = self._current_time()
        refresh_token = self._new_refresh_token(issued_at)

        try:
            created_records = (
                await self.auth_store.create_password_user_with_session(
                    email=normalized_email,
                    password_hash=password_hash,
                    name=normalized_name,
                    token_hash=refresh_token.token_hash,
                    family_id=str(uuid4()),
                    session_expires_at=refresh_token.expires_at,
                )
            )
        except UserStoreError as error:
            if "conflict_fields" not in error.details:
                raise

            raise InvalidInputError(
                technical_message="An account already uses this email.",
                details={"field": "email", "code": "already_exists"},
            ) from error

        return self._authentication_result(
            user=created_records.user,
            refresh_token=refresh_token,
        )

    async def login_with_password(
        self,
        *,
        email: str,
        password: str,
    ) -> AuthenticationResult:
        """Authenticate a local account without revealing account existence."""

        normalized_email = _login_email(email)
        user = await self.auth_store.get_user_by_email(normalized_email)
        stored_password_hash = user.password_hash if user is not None else None
        password_matches, updated_password_hash = (
            self.password_hasher.verify_and_update(
                password,
                stored_password_hash,
            )
        )

        if user is None or not password_matches:
            raise _invalid_credentials()

        _require_active_user(user)

        if updated_password_hash is not None:
            user = await self.auth_store.update_password_hash(
                user.user_id,
                updated_password_hash,
            )

        refresh_token = self._new_refresh_token(self._current_time())
        await self.auth_store.create_session(
            user_id=user.user_id,
            token_hash=refresh_token.token_hash,
            family_id=str(uuid4()),
            expires_at=refresh_token.expires_at,
        )

        return self._authentication_result(
            user=user,
            refresh_token=refresh_token,
        )

    async def login_with_google(
        self,
        google_id_token: str,
    ) -> AuthenticationResult:
        """Authenticate a verified Google identity without implicit linking."""

        google_token_verifier = self.google_token_verifier

        if google_token_verifier is None:
            raise AuthConfigurationError(
                technical_message="Google authentication is not configured.",
            )

        google_identity = google_token_verifier.verify(google_id_token)

        if not google_identity.email_verified:
            raise EmailVerificationRequiredError(
                technical_message="Google email verification is required.",
            )

        user = await self.auth_store.get_user_by_google_sub(
            google_identity.subject
        )

        if user is not None:
            _require_active_user(user)
            return await self._create_session_and_authentication_result(user)

        user_with_same_email = await self.auth_store.get_user_by_email(
            google_identity.email
        )

        if user_with_same_email is not None:
            raise AccountLinkRequiredError(
                technical_message=(
                    "An existing account requires explicit Google linking."
                ),
            )

        issued_at = self._current_time()
        refresh_token = self._new_refresh_token(issued_at)

        try:
            created_records = (
                await self.auth_store.create_google_user_with_session(
                    email=google_identity.email,
                    google_subject=google_identity.subject,
                    email_verified_at=issued_at,
                    name=google_identity.name,
                    avatar_url=google_identity.avatar_url,
                    token_hash=refresh_token.token_hash,
                    family_id=str(uuid4()),
                    session_expires_at=refresh_token.expires_at,
                )
            )
        except UserStoreError as error:
            return await self._resolve_google_creation_conflict(
                google_subject=google_identity.subject,
                email=google_identity.email,
                error=error,
            )

        return self._authentication_result(
            user=created_records.user,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> AuthenticationResult:
        """Rotate one refresh token and issue a new token pair.

        Lookup, row locking, expiration checks, reuse detection, revocation,
        and replacement creation are executed by ``AuthStore`` in one
        transaction.
        """

        current_token_hash = self._refresh_token_digest(refresh_token)
        checked_at = self._current_time()
        replacement_token = self._new_refresh_token(checked_at)
        rotation = await self.auth_store.rotate_session_by_token_hash(
            current_token_hash=current_token_hash,
            replacement_token_hash=replacement_token.token_hash,
            replacement_expires_at=replacement_token.expires_at,
            checked_at=checked_at,
        )

        if rotation.status != "rotated":
            raise _invalid_refresh_token()

        if rotation.user is None or rotation.replacement_session is None:
            raise RuntimeError(
                "Successful refresh rotation returned incomplete records."
            )

        if rotation.user.disabled:
            await self.auth_store.revoke_user_sessions(rotation.user.user_id)
            raise AccountDisabledError(
                technical_message=(
                    "Authentication is disabled for this account."
                ),
            )

        return self._authentication_result(
            user=rotation.user,
            refresh_token=replacement_token,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh-token family without revealing token validity."""

        try:
            token_hash = self._refresh_token_digest(refresh_token)
        except RefreshTokenInvalidError:
            return

        auth_session = await self.auth_store.get_session_by_token_hash(
            token_hash
        )

        if auth_session is None:
            return

        await self.auth_store.revoke_session_family(auth_session.family_id)

    async def authenticate_access_token(
        self,
        access_token: str,
    ) -> AuthenticatedPrincipal:
        """Validate an access JWT and load the current active user identity."""

        claims = self.access_token_service.decode(access_token)
        user = await self.auth_store.get_user(claims.user_id)

        if user is None:
            raise InvalidTokenError(
                technical_message="Access token user no longer exists.",
            )

        _require_active_user(user)
        return _principal_from_user(user)

    async def _create_session_and_authentication_result(
        self,
        user: AuthUserRecord,
    ) -> AuthenticationResult:
        """Create a committed refresh session for an existing user."""

        refresh_token = self._new_refresh_token(self._current_time())
        await self.auth_store.create_session(
            user_id=user.user_id,
            token_hash=refresh_token.token_hash,
            family_id=str(uuid4()),
            expires_at=refresh_token.expires_at,
        )
        return self._authentication_result(
            user=user,
            refresh_token=refresh_token,
        )

    async def _resolve_google_creation_conflict(
        self,
        *,
        google_subject: str,
        email: str,
        error: UserStoreError,
    ) -> AuthenticationResult:
        """Resolve concurrent Google registration without linking by email."""

        existing_google_user = await self.auth_store.get_user_by_google_sub(
            google_subject
        )

        if existing_google_user is not None:
            _require_active_user(existing_google_user)
            return await self._create_session_and_authentication_result(
                existing_google_user
            )

        existing_email_user = await self.auth_store.get_user_by_email(email)

        if existing_email_user is not None:
            raise AccountLinkRequiredError(
                technical_message=(
                    "An existing account requires explicit Google linking."
                ),
            ) from error

        raise error

    def _new_refresh_token(
        self,
        issued_at: datetime,
    ) -> _RefreshTokenMaterial:
        token = self.refresh_token_generator.generate()
        return _RefreshTokenMaterial(
            token=token,
            token_hash=self.refresh_token_generator.digest(token),
            expires_at=issued_at
            + timedelta(seconds=self.refresh_token_ttl_seconds),
        )

    def _refresh_token_digest(self, refresh_token: str) -> str:
        try:
            return self.refresh_token_generator.digest(refresh_token)
        except (TypeError, ValueError) as error:
            raise _invalid_refresh_token() from error

    def _authentication_result(
        self,
        *,
        user: AuthUserRecord,
        refresh_token: _RefreshTokenMaterial,
    ) -> AuthenticationResult:
        principal = _principal_from_user(user)
        access_token = self.access_token_service.issue(principal)
        access_token_claims = self.access_token_service.decode(access_token)
        tokens = IssuedAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token.token,
            access_token_expires_at=access_token_claims.expires_at,
            refresh_token_expires_at=refresh_token.expires_at,
        )
        return AuthenticationResult(principal=principal, tokens=tokens)

    def _current_time(self) -> datetime:
        return _utc_datetime(self._clock(), field_name="clock")


def _principal_from_user(user: AuthUserRecord) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
        email_verified=user.email_verified,
    )


def _require_active_user(user: AuthUserRecord) -> None:
    if user.disabled:
        raise AccountDisabledError(
            technical_message="Authentication is disabled for this account.",
        )


def _registration_email(value: object) -> str:
    try:
        return _normalized_email(value)
    except (TypeError, ValueError) as error:
        raise InvalidInputError(
            technical_message="Registration email is invalid.",
            details={"field": "email"},
        ) from error


def _login_email(value: object) -> str:
    try:
        return _normalized_email(value)
    except (TypeError, ValueError) as error:
        raise _invalid_credentials() from error


def _normalized_email(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("email must be a string.")

    normalized_email = value.strip().lower()

    if not normalized_email or len(normalized_email) > MAXIMUM_AUTH_EMAIL_LENGTH:
        raise ValueError("email has an invalid length.")

    local_part, separator, domain = normalized_email.rpartition("@")

    if (
        separator != "@"
        or not local_part
        or not domain
        or "@" in local_part
        or any(character.isspace() for character in normalized_email)
    ):
        raise ValueError("email has an invalid format.")

    return normalized_email


def _optional_name(value: object) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise InvalidInputError(
            technical_message="Registration name must be a string.",
            details={"field": "name"},
        )

    normalized_name = value.strip()

    if len(normalized_name) > MAXIMUM_AUTH_NAME_LENGTH:
        raise InvalidInputError(
            technical_message="Registration name is too long.",
            details={"field": "name"},
        )

    return normalized_name or None


def _password_hash_for_registration(
    password_hasher: PasswordHasher,
    password: str,
) -> str:
    try:
        return password_hasher.hash(password)
    except (TypeError, ValueError) as error:
        raise InvalidInputError(
            technical_message="Registration password is invalid.",
            details={"field": "password"},
        ) from error


def _invalid_credentials() -> InvalidCredentialsError:
    return InvalidCredentialsError(
        technical_message="Email or password could not be authenticated.",
    )


def _invalid_refresh_token() -> RefreshTokenInvalidError:
    return RefreshTokenInvalidError(
        technical_message="Refresh token could not be accepted.",
    )


def _positive_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AuthConfigurationError(
            technical_message=f"{field_name} must be a positive integer.",
        )

    return value


def _utc_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise AuthConfigurationError(
            technical_message=f"{field_name} must return a datetime.",
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise AuthConfigurationError(
            technical_message=f"{field_name} must include timezone data.",
        )

    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AuthenticationResult",
    "AuthService",
]
