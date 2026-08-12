"""Public HTTP contracts for authentication endpoints.

These schemas validate request and response payloads at the API boundary. They
contain no authentication, persistence, token-signing, cookie, or Google
verification logic. Refresh tokens are deliberately absent because routers
transport them exclusively through protected HTTP-only cookies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.auth.principal import (
    AuthenticatedPrincipal,
    IssuedAuthTokens,
)
from app.auth.passwords import DEFAULT_MIN_PASSWORD_LENGTH


MAXIMUM_EMAIL_LENGTH = 320
MAXIMUM_NAME_LENGTH = 255
MAXIMUM_PASSWORD_LENGTH = 128
MAXIMUM_GOOGLE_ID_TOKEN_LENGTH = 16_384
MAXIMUM_ACCESS_TOKEN_LENGTH = 16_384
MAXIMUM_PASSWORD_RESET_TOKEN_LENGTH = 512

NormalizedEmail: TypeAlias = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=MAXIMUM_EMAIL_LENGTH,
    ),
]
OptionalName: TypeAlias = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAXIMUM_NAME_LENGTH,
    ),
]


class _AuthenticationSchema(BaseModel):
    """Apply strict behavior shared by public authentication contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class _EmailCredentialsRequest(_AuthenticationSchema):
    """Provide normalized email validation shared by password requests."""

    email: NormalizedEmail = Field(
        description="Email address used to identify the account.",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize case and reject structurally invalid email addresses."""

        return _normalize_email_address(value)


class RegisterRequest(_EmailCredentialsRequest):
    """Request body for creating a password-authenticated account."""

    password: str = Field(
        min_length=1,
        max_length=MAXIMUM_PASSWORD_LENGTH,
        repr=False,
        description="Plain password to hash during account registration.",
    )
    name: OptionalName = Field(
        description="Display name for the new account.",
    )


class RegisterResponse(_AuthenticationSchema):
    """Response returned while an account waits for email confirmation."""

    email: NormalizedEmail = Field(
        description="Email address that received the confirmation link.",
    )
    email_verification_required: Literal[True] = True


class ResendEmailVerificationRequest(_EmailCredentialsRequest):
    """Request used to request another confirmation email."""


class ForgotPasswordRequest(_EmailCredentialsRequest):
    """Request used to start password recovery for an account email."""


class PasswordResetRequestedResponse(_AuthenticationSchema):
    """Neutral response for every accepted password-reset request."""

    accepted: Literal[True] = Field(
        default=True,
        description=(
            "Indicates that the request was accepted without revealing "
            "whether the email belongs to an account."
        ),
    )


class ResetPasswordRequest(_AuthenticationSchema):
    """Request used to replace a password with a valid reset token."""

    token: str = Field(
        min_length=1,
        max_length=MAXIMUM_PASSWORD_RESET_TOKEN_LENGTH,
        repr=False,
        description="Opaque token received in the password-reset email.",
    )
    new_password: str = Field(
        min_length=DEFAULT_MIN_PASSWORD_LENGTH,
        max_length=MAXIMUM_PASSWORD_LENGTH,
        repr=False,
        description="New password to hash and store for the account.",
    )

    @field_validator("token")
    @classmethod
    def reject_surrounding_token_whitespace(cls, value: str) -> str:
        """Reject altered token input instead of silently normalizing it."""

        if value != value.strip():
            raise ValueError("token must not contain outer whitespace")

        return value


class PasswordLoginRequest(_EmailCredentialsRequest):
    """Request body for authenticating an account with a password."""

    password: str = Field(
        min_length=DEFAULT_MIN_PASSWORD_LENGTH,
        max_length=MAXIMUM_PASSWORD_LENGTH,
        repr=False,
        description="Plain password submitted for verification.",
    )


class GoogleLoginRequest(_AuthenticationSchema):
    """Request body carrying a Google-issued ID token for verification."""

    google_id_token: str = Field(
        min_length=1,
        max_length=MAXIMUM_GOOGLE_ID_TOKEN_LENGTH,
        repr=False,
        description="Signed Google ID token issued to the frontend client.",
    )

    @field_validator("google_id_token")
    @classmethod
    def reject_surrounding_whitespace(cls, value: str) -> str:
        """Reject altered token input instead of silently normalizing it."""

        if value != value.strip():
            raise ValueError("google_id_token must not contain outer whitespace")

        return value


class AccessTokenResponse(_AuthenticationSchema):
    """Public access credential returned after successful authentication.

    The corresponding refresh token is intentionally omitted and must be set
    by the router as a protected HTTP-only cookie.
    """

    access_token: str = Field(
        min_length=1,
        max_length=MAXIMUM_ACCESS_TOKEN_LENGTH,
        repr=False,
        description="Short-lived JWT used in the Authorization header.",
    )
    token_type: Literal["bearer"] = Field(
        default="bearer",
        description="Authorization scheme used with the access token.",
    )
    access_token_expires_at: datetime = Field(
        description="Timezone-aware expiration timestamp for the access token.",
    )

    @field_validator("access_token")
    @classmethod
    def reject_modified_access_token(cls, value: str) -> str:
        """Reject whitespace around bearer credentials."""

        if value != value.strip():
            raise ValueError("access_token must not contain outer whitespace")

        return value

    @field_validator("access_token_expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Require an unambiguous token expiration timestamp."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("access_token_expires_at must include a timezone")

        return value

    @classmethod
    def from_issued_tokens(cls, tokens: IssuedAuthTokens) -> Self:
        """Create an HTTP response without exposing the refresh token."""

        return cls(
            access_token=tokens.access_token,
            token_type=tokens.token_type,
            access_token_expires_at=tokens.access_token_expires_at,
        )


class CurrentUserResponse(_AuthenticationSchema):
    """Public identity returned for the currently authenticated account."""

    user_id: int = Field(
        gt=0,
        description="Internal identifier of the authenticated user.",
    )
    email: NormalizedEmail = Field(
        description="Normalized email address of the authenticated user.",
    )
    name: OptionalName | None = Field(
        default=None,
        description="Optional display name of the authenticated user.",
    )
    auth_provider: str = Field(
        min_length=1,
        max_length=50,
        description="Provider used to authenticate the account.",
    )
    email_verified: bool = Field(
        description="Whether the account email has been verified.",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Keep directly constructed responses consistent with principals."""

        return _normalize_email_address(value)

    @classmethod
    def from_principal(cls, principal: AuthenticatedPrincipal) -> Self:
        """Map a verified internal principal to its safe HTTP representation."""

        return cls(
            user_id=principal.user_id,
            email=principal.email,
            name=principal.name,
            auth_provider=principal.auth_provider,
            email_verified=principal.email_verified,
        )


def _normalize_email_address(value: str) -> str:
    normalized_email = value.lower()
    local_part, separator, domain = normalized_email.rpartition("@")

    if (
        separator != "@"
        or not local_part
        or not domain
        or "@" in local_part
        or any(character.isspace() for character in normalized_email)
    ):
        raise ValueError("email must be a valid address")

    return normalized_email

class VerifyEmailRequest(_AuthenticationSchema):
    """Request used to confirm an email verification token."""

    token: str


class ResendEmailVerificationResponse(_AuthenticationSchema):
    """Response returned after requesting a new verification email."""

    sent: Literal[True] = True

__all__ = [
    "AccessTokenResponse",
    "CurrentUserResponse",
    "ForgotPasswordRequest",
    "GoogleLoginRequest",
    "PasswordLoginRequest",
    "RegisterRequest",
    "RegisterResponse",
    "ResendEmailVerificationRequest",
    "ResendEmailVerificationResponse",
    "PasswordResetRequestedResponse",
    "ResetPasswordRequest",
    "VerifyEmailRequest",
]
