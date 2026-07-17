"""Immutable authentication contracts shared by application layers.

The objects in this module contain only verified identity and token metadata.
They do not access the database, encode tokens, verify OAuth providers, or
depend on FastAPI and SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticatedPrincipal:
    """Verified application identity exposed to protected use cases."""

    user_id: int
    email: str
    name: str | None
    auth_provider: str
    email_verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "user_id",
            _positive_user_id(self.user_id),
        )
        object.__setattr__(
            self,
            "email",
            _normalized_email(self.email),
        )
        object.__setattr__(
            self,
            "name",
            _optional_text(self.name, field_name="name"),
        )
        object.__setattr__(
            self,
            "auth_provider",
            _required_text(
                self.auth_provider,
                field_name="auth_provider",
            ).lower(),
        )
        _require_bool(self.email_verified, field_name="email_verified")


@dataclass(frozen=True, slots=True, kw_only=True)
class GoogleIdentity:
    """Identity claims verified from a signed Google ID token."""

    subject: str
    email: str
    email_verified: bool
    name: str | None = None
    avatar_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject",
            _required_text(self.subject, field_name="subject"),
        )
        object.__setattr__(
            self,
            "email",
            _normalized_email(self.email),
        )
        _require_bool(self.email_verified, field_name="email_verified")
        object.__setattr__(
            self,
            "name",
            _optional_text(self.name, field_name="name"),
        )
        object.__setattr__(
            self,
            "avatar_url",
            _optional_text(self.avatar_url, field_name="avatar_url"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AccessTokenClaims:
    """Validated claims extracted from an application access token."""

    user_id: int
    token_id: str
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    token_type: Literal["access"] = "access"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "user_id",
            _positive_user_id(self.user_id),
        )
        object.__setattr__(
            self,
            "token_id",
            _required_text(self.token_id, field_name="token_id"),
        )

        issued_at = _utc_datetime(self.issued_at, field_name="issued_at")
        not_before = _utc_datetime(
            self.not_before,
            field_name="not_before",
        )
        expires_at = _utc_datetime(
            self.expires_at,
            field_name="expires_at",
        )

        if expires_at <= issued_at:
            raise ValueError("expires_at must be later than issued_at.")

        if not_before > expires_at:
            raise ValueError("not_before must not be later than expires_at.")

        if self.token_type != "access":
            raise ValueError("token_type must be 'access'.")

        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "not_before", not_before)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True, kw_only=True)
class IssuedAuthTokens:
    """Tokens issued after successful authentication or refresh."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    token_type: Literal["bearer"] = "bearer"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "access_token",
            _required_text(
                self.access_token,
                field_name="access_token",
            ),
        )
        object.__setattr__(
            self,
            "refresh_token",
            _required_text(
                self.refresh_token,
                field_name="refresh_token",
            ),
        )

        access_expires_at = _utc_datetime(
            self.access_token_expires_at,
            field_name="access_token_expires_at",
        )
        refresh_expires_at = _utc_datetime(
            self.refresh_token_expires_at,
            field_name="refresh_token_expires_at",
        )

        if refresh_expires_at <= access_expires_at:
            raise ValueError(
                "refresh_token_expires_at must be later than "
                "access_token_expires_at."
            )

        if self.token_type != "bearer":
            raise ValueError("token_type must be 'bearer'.")

        object.__setattr__(
            self,
            "access_token_expires_at",
            access_expires_at,
        )
        object.__setattr__(
            self,
            "refresh_token_expires_at",
            refresh_expires_at,
        )


def _positive_user_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("user_id must be a positive integer.")

    return value


def _normalized_email(value: object) -> str:
    email = _required_text(value, field_name="email").lower()
    local_part, separator, domain = email.rpartition("@")

    if (
        separator != "@"
        or not local_part
        or not domain
        or "@" in local_part
        or any(character.isspace() for character in email)
    ):
        raise ValueError("email must be a valid normalized address.")

    return email


def _required_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be blank.")

    return normalized


def _optional_text(
    value: object,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    return value.strip() or None


def _require_bool(value: object, *, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")


def _utc_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information.")

    return value.astimezone(timezone.utc)


__all__ = [
    "AccessTokenClaims",
    "AuthenticatedPrincipal",
    "GoogleIdentity",
    "IssuedAuthTokens",
]
