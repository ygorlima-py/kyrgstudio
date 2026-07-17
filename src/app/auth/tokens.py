"""Issue and validate application-owned authentication tokens.

Access tokens are short-lived signed JWTs. Refresh tokens are opaque random
values whose deterministic digest can be persisted without storing the bearer
credential itself. This module performs no database, HTTP, OAuth, or settings
loading operations and never logs token material.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Final, Literal
from uuid import uuid4

import jwt
from jwt.exceptions import PyJWTError

from app.auth.principal import AccessTokenClaims, AuthenticatedPrincipal
from app.errors import AuthConfigurationError, InvalidTokenError


AccessTokenAlgorithm = Literal["HS256"]

ACCESS_TOKEN_TYPE: Final = "access"
DEFAULT_ACCESS_TOKEN_TTL_SECONDS: Final = 15 * 60
DEFAULT_ALLOWED_CLOCK_SKEW_SECONDS: Final = 30
DEFAULT_REFRESH_TOKEN_BYTES: Final = 48
MINIMUM_REFRESH_TOKEN_BYTES: Final = 32
MINIMUM_SIGNING_SECRET_BYTES: Final = 32
MAXIMUM_ENCODED_ACCESS_TOKEN_LENGTH: Final = 16_384
MAXIMUM_REFRESH_TOKEN_LENGTH: Final = 1_024

_REQUIRED_ACCESS_TOKEN_CLAIMS: Final = (
    "sub",
    "iss",
    "aud",
    "exp",
    "iat",
    "nbf",
    "jti",
    "type",
)
_POSITIVE_DECIMAL_PATTERN: Final = re.compile(r"^[1-9][0-9]*$")


class AccessTokenService:
    """Issue and validate Kyrg Studio access tokens using a fixed algorithm.

    Configuration is supplied once when the service is constructed. During
    decoding, the accepted algorithm comes exclusively from this trusted
    configuration and never from the token header.
    """

    __slots__ = (
        "_audience",
        "_issuer",
        "_secret",
        "algorithm",
        "allowed_clock_skew_seconds",
        "ttl_seconds",
    )

    def __init__(
        self,
        *,
        secret: str,
        issuer: str,
        audience: str,
        algorithm: AccessTokenAlgorithm = "HS256",
        ttl_seconds: int = DEFAULT_ACCESS_TOKEN_TTL_SECONDS,
        allowed_clock_skew_seconds: int = (
            DEFAULT_ALLOWED_CLOCK_SKEW_SECONDS
        ),
    ) -> None:
        """Create a token service from already-loaded application settings."""

        self._secret = _signing_secret(secret)
        self._issuer = _configuration_text(issuer, field_name="issuer")
        self._audience = _configuration_text(
            audience,
            field_name="audience",
        )

        if algorithm != "HS256":
            raise AuthConfigurationError(
                technical_message="Unsupported access token algorithm.",
                details={"algorithm": algorithm},
            )

        self.algorithm = algorithm
        self.ttl_seconds = _positive_configuration_integer(
            ttl_seconds,
            field_name="ttl_seconds",
        )
        self.allowed_clock_skew_seconds = (
            _non_negative_configuration_integer(
                allowed_clock_skew_seconds,
                field_name="allowed_clock_skew_seconds",
            )
        )

        if self.allowed_clock_skew_seconds >= self.ttl_seconds:
            raise AuthConfigurationError(
                technical_message=(
                    "Access token clock skew must be lower than its TTL."
                ),
            )

    def issue(self, principal: AuthenticatedPrincipal) -> str:
        """Return a signed, short-lived access JWT for a verified principal."""

        if not isinstance(principal, AuthenticatedPrincipal):
            raise TypeError(
                "principal must be an AuthenticatedPrincipal instance."
            )

        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=self.ttl_seconds)
        payload: dict[str, object] = {
            "sub": str(principal.user_id),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expires_at,
            "jti": uuid4().hex,
            "type": ACCESS_TOKEN_TYPE,
        }

        try:
            return jwt.encode(
                payload,
                self._secret,
                algorithm=self.algorithm,
            )
        except PyJWTError as error:
            raise AuthConfigurationError(
                technical_message="Failed to issue an access token.",
            ) from error

    def decode(self, token: str) -> AccessTokenClaims:
        """Validate a JWT and return trusted, application-level claims.

        Expiration, signature, algorithm, issuer, audience, required claims,
        and the application token type are all validated before any claim is
        exposed to callers.
        """

        encoded_token = _encoded_access_token(token)

        try:
            payload = jwt.decode(
                encoded_token,
                self._secret,
                algorithms=[self.algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self.allowed_clock_skew_seconds,
                options={
                    "require": list(_REQUIRED_ACCESS_TOKEN_CLAIMS),
                    "strict_aud": True,
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_sub": True,
                    "verify_jti": True,
                },
            )
            return _access_token_claims(payload)
        except (PyJWTError, TypeError, ValueError, OverflowError) as error:
            raise InvalidTokenError(
                technical_message="Access token validation failed.",
            ) from error


class RefreshTokenGenerator:
    """Generate opaque refresh tokens and deterministic storage digests.

    The generated bearer token must be returned to the authenticated client.
    Only the SHA-256 hexadecimal digest returned by :meth:`digest` belongs in
    persistent storage.
    """

    __slots__ = ("token_bytes",)

    def __init__(
        self,
        *,
        token_bytes: int = DEFAULT_REFRESH_TOKEN_BYTES,
    ) -> None:
        validated_token_bytes = _positive_configuration_integer(
            token_bytes,
            field_name="token_bytes",
        )

        if validated_token_bytes < MINIMUM_REFRESH_TOKEN_BYTES:
            raise AuthConfigurationError(
                technical_message=(
                    "Refresh tokens require at least "
                    f"{MINIMUM_REFRESH_TOKEN_BYTES} random bytes."
                ),
            )

        self.token_bytes = validated_token_bytes

    def generate(self) -> str:
        """Return a URL-safe refresh token from the operating-system CSPRNG."""

        return secrets.token_urlsafe(self.token_bytes)

    def digest(self, token: str) -> str:
        """Return the stable SHA-256 digest used to locate a refresh session."""

        normalized_token = _refresh_token(token)
        return hashlib.sha256(normalized_token.encode("utf-8")).hexdigest()


def _access_token_claims(payload: dict[str, object]) -> AccessTokenClaims:
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise ValueError("Unexpected access token type.")

    return AccessTokenClaims(
        user_id=_subject_user_id(payload.get("sub")),
        token_id=_claim_text(payload.get("jti"), field_name="jti"),
        issued_at=_numeric_date(payload.get("iat"), field_name="iat"),
        not_before=_numeric_date(payload.get("nbf"), field_name="nbf"),
        expires_at=_numeric_date(payload.get("exp"), field_name="exp"),
        token_type="access",
    )


def _subject_user_id(value: object) -> int:
    if not isinstance(value, str) or _POSITIVE_DECIMAL_PATTERN.fullmatch(
        value
    ) is None:
        raise ValueError("Access token subject is invalid.")

    return int(value)


def _numeric_date(value: object, *, field_name: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Access token claim '{field_name}' is invalid.")

    return datetime.fromtimestamp(value, tz=timezone.utc)


def _claim_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Access token claim '{field_name}' is invalid.")

    normalized_value = value.strip()

    if not normalized_value or normalized_value != value:
        raise ValueError(f"Access token claim '{field_name}' is invalid.")

    return normalized_value


def _encoded_access_token(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidTokenError(
            technical_message="Access token must be a string.",
        )

    if (
        not value
        or value != value.strip()
        or len(value) > MAXIMUM_ENCODED_ACCESS_TOKEN_LENGTH
    ):
        raise InvalidTokenError(
            technical_message="Access token has an invalid format.",
        )

    return value


def _refresh_token(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("refresh token must be a string.")

    if (
        not value
        or value != value.strip()
        or len(value) > MAXIMUM_REFRESH_TOKEN_LENGTH
    ):
        raise ValueError("refresh token has an invalid format.")

    return value


def _signing_secret(value: object) -> str:
    if not isinstance(value, str):
        raise AuthConfigurationError(
            technical_message="Access token signing secret must be a string.",
        )

    if value != value.strip() or len(value.encode("utf-8")) < (
        MINIMUM_SIGNING_SECRET_BYTES
    ):
        raise AuthConfigurationError(
            technical_message=(
                "Access token signing secret is missing or too short."
            ),
        )

    return value


def _configuration_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthConfigurationError(
            technical_message=f"Access token {field_name} is required.",
        )

    if value != value.strip():
        raise AuthConfigurationError(
            technical_message=(
                f"Access token {field_name} must not contain outer whitespace."
            ),
        )

    return value


def _positive_configuration_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AuthConfigurationError(
            technical_message=f"{field_name} must be a positive integer.",
        )

    return value


def _non_negative_configuration_integer(
    value: object,
    *,
    field_name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuthConfigurationError(
            technical_message=(
                f"{field_name} must be a non-negative integer."
            ),
        )

    return value


__all__ = [
    "AccessTokenService",
    "RefreshTokenGenerator",
]
