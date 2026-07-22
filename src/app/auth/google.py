"""Verify Google-issued ID tokens and expose minimal trusted identities.

This module delegates cryptographic verification to ``google-auth``. It never
accepts identity fields supplied separately by a client, persists users, links
accounts, or performs application login decisions. Only claims from a verified
Google ID token are converted into :class:`GoogleIdentity`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token

from app.auth.principal import GoogleIdentity
from app.errors import AuthConfigurationError, InvalidCredentialsError


MAXIMUM_GOOGLE_ID_TOKEN_LENGTH: Final = 16_384
MAXIMUM_GOOGLE_SUBJECT_LENGTH: Final = 255
MAXIMUM_GOOGLE_EMAIL_LENGTH: Final = 320
MAXIMUM_GOOGLE_NAME_LENGTH: Final = 255
MAXIMUM_GOOGLE_AVATAR_URL_LENGTH: Final = 2_048

_GOOGLE_ISSUERS: Final = frozenset(
    {
        "accounts.google.com",
        "https://accounts.google.com",
    }
)


class GoogleTokenVerifier:
    """Verify Google OAuth 2.0 ID tokens for configured application clients.

    The verifier is configured once and can be reused across requests. Google
    performs key rotation, so ``google-auth`` obtains the current public keys
    through the provided transport before validating signature and claims.

    Args:
        client_ids: Google OAuth client IDs allowed to authenticate users.
        allowed_clock_skew_seconds: Small tolerance for clock differences when
            validating issued-at and expiration claims.
        request: Optional Google Auth HTTP transport, primarily useful for
            sharing a configured session or replacing transport in tests.
    """

    __slots__ = (
        "_accepted_client_ids",
        "_google_auth_request",
        "allowed_clock_skew_seconds",
    )

    def __init__(
        self,
        *,
        client_ids: Sequence[str],
        allowed_clock_skew_seconds: int = 0,
        request: GoogleAuthRequest | None = None,
    ) -> None:
        self._accepted_client_ids = _validated_client_ids(client_ids)
        self.allowed_clock_skew_seconds = _non_negative_integer(
            allowed_clock_skew_seconds,
            field_name="allowed_clock_skew_seconds",
        )
        self._google_auth_request = (
            request if request is not None else GoogleAuthRequest()
        )

    def verify(self, id_token: str) -> GoogleIdentity:
        """Return the minimal identity from a cryptographically verified token.

        Invalid signatures, expiration, issuer, audience, and malformed claims
        produce the same public credential error. The submitted token and its
        claims are never included in error details or logs.
        """

        encoded_id_token = _validated_encoded_id_token(id_token)

        try:
            verified_claims = google_id_token.verify_oauth2_token(
                encoded_id_token,
                self._google_auth_request,
                audience=self._verification_audience(),
                clock_skew_in_seconds=self.allowed_clock_skew_seconds,
            )
            return _identity_from_verified_claims(
                verified_claims,
                accepted_client_ids=self._accepted_client_ids,
            )
        except TransportError as error:
            raise AuthConfigurationError(
                technical_message=(
                    "Google identity verification is temporarily unavailable."
                ),
            ) from error
        except (GoogleAuthError, KeyError, TypeError, ValueError) as error:
            raise InvalidCredentialsError(
                technical_message="Google ID token verification failed.",
            ) from error

    def _verification_audience(self) -> str | list[str]:
        """Return the audience shape accepted by the Google verification API."""

        if len(self._accepted_client_ids) == 1:
            return self._accepted_client_ids[0]

        return list(self._accepted_client_ids)


def _identity_from_verified_claims(
    claims: Mapping[str, Any],
    *,
    accepted_client_ids: tuple[str, ...],
) -> GoogleIdentity:
    """Convert already-verified Google claims into the internal contract."""

    _require_verified_issuer(claims.get("iss"))
    _require_verified_audience(
        claims.get("aud"),
        accepted_client_ids=accepted_client_ids,
    )

    return GoogleIdentity(
        subject=_required_claim_text(
            claims.get("sub"),
            claim_name="sub",
            maximum_length=MAXIMUM_GOOGLE_SUBJECT_LENGTH,
        ),
        email=_required_claim_text(
            claims.get("email"),
            claim_name="email",
            maximum_length=MAXIMUM_GOOGLE_EMAIL_LENGTH,
        ),
        email_verified=_required_boolean_claim(
            claims.get("email_verified"),
            claim_name="email_verified",
        ),
        name=_optional_claim_text(
            claims.get("name"),
            claim_name="name",
            maximum_length=MAXIMUM_GOOGLE_NAME_LENGTH,
        ),
        avatar_url=_optional_claim_text(
            claims.get("picture"),
            claim_name="picture",
            maximum_length=MAXIMUM_GOOGLE_AVATAR_URL_LENGTH,
        ),
    )


def _validated_client_ids(client_ids: object) -> tuple[str, ...]:
    if isinstance(client_ids, (str, bytes)) or not isinstance(
        client_ids,
        Sequence,
    ):
        raise AuthConfigurationError(
            technical_message=(
                "Google client IDs must be provided as a sequence."
            ),
        )

    normalized_client_ids: list[str] = []

    for client_id in client_ids:
        if not isinstance(client_id, str):
            raise AuthConfigurationError(
                technical_message="Every Google client ID must be a string.",
            )

        normalized_client_id = client_id.strip()

        if (
            not normalized_client_id
            or normalized_client_id != client_id
            or "*" in normalized_client_id
        ):
            raise AuthConfigurationError(
                technical_message="Google client ID configuration is invalid.",
            )

        if normalized_client_id not in normalized_client_ids:
            normalized_client_ids.append(normalized_client_id)

    if not normalized_client_ids:
        raise AuthConfigurationError(
            technical_message="At least one Google client ID is required.",
        )

    return tuple(normalized_client_ids)


def _validated_encoded_id_token(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidCredentialsError(
            technical_message="Google ID token must be a string.",
        )

    if (
        not value
        or value != value.strip()
        or len(value) > MAXIMUM_GOOGLE_ID_TOKEN_LENGTH
    ):
        raise InvalidCredentialsError(
            technical_message="Google ID token has an invalid format.",
        )

    return value


def _require_verified_issuer(value: object) -> None:
    if not isinstance(value, str) or value not in _GOOGLE_ISSUERS:
        raise ValueError("Google issuer claim is invalid.")


def _require_verified_audience(
    value: object,
    *,
    accepted_client_ids: tuple[str, ...],
) -> None:
    if not isinstance(value, str) or value not in accepted_client_ids:
        raise ValueError("Google audience claim is invalid.")


def _required_claim_text(
    value: object,
    *,
    claim_name: str,
    maximum_length: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Google claim '{claim_name}' must be a string.")

    normalized_value = value.strip()

    if not normalized_value or len(normalized_value) > maximum_length:
        raise ValueError(f"Google claim '{claim_name}' is invalid.")

    return normalized_value


def _optional_claim_text(
    value: object,
    *,
    claim_name: str,
    maximum_length: int,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"Google claim '{claim_name}' must be a string.")

    normalized_value = value.strip()

    if not normalized_value:
        return None

    if len(normalized_value) > maximum_length:
        raise ValueError(f"Google claim '{claim_name}' is too long.")

    return normalized_value


def _required_boolean_claim(value: object, *, claim_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Google claim '{claim_name}' must be a boolean.")

    return value


def _non_negative_integer(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuthConfigurationError(
            technical_message=(
                f"{field_name} must be a non-negative integer."
            ),
        )

    return value


__all__ = ["GoogleTokenVerifier"]
