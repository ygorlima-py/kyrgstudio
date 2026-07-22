"""Unit tests for application-owned access and refresh tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest

from app.auth.principal import AuthenticatedPrincipal
from app.auth.tokens import AccessTokenService, RefreshTokenGenerator
from app.errors import AuthConfigurationError, InvalidTokenError


SECRET = "s" * 32
OTHER_SECRET = "x" * 32
ISSUER = "kyrg-studio"
AUDIENCE = "kyrg-api"
NOW = datetime.now(timezone.utc)


def _token_service(**overrides: object) -> AccessTokenService:
    configuration: dict[str, object] = {
        "secret": SECRET,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "ttl_seconds": 900,
        "allowed_clock_skew_seconds": 0,
    }
    configuration.update(overrides)
    return AccessTokenService(**configuration)  # type: ignore[arg-type]


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=17,
        email="user@example.com",
        name="Ada",
        auth_provider="password",
        email_verified=True,
    )


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sub": "17",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": NOW - timedelta(seconds=1),
        "nbf": NOW - timedelta(seconds=1),
        "exp": NOW + timedelta(minutes=15),
        "jti": "token-id",
        "type": "access",
    }
    payload.update(overrides)
    return payload


def _encode(
    payload: dict[str, object],
    *,
    secret: str = SECRET,
    algorithm: str = "HS256",
) -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def test_issue_creates_access_jwt_with_required_claims() -> None:
    """Issue a signed JWT containing every required application claim."""

    token = _token_service().issue(_principal())

    payload: dict[str, Any] = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    assert payload["sub"] == "17"
    assert payload["iss"] == ISSUER
    assert payload["aud"] == AUDIENCE
    assert payload["type"] == "access"
    assert payload["jti"]
    assert payload["iat"] <= payload["exp"]
    assert payload["nbf"] <= payload["exp"]


def test_issue_generates_unique_jti_for_each_token() -> None:
    """Assign a unique identifier even to immediately consecutive tokens."""

    service = _token_service()
    first_token = service.issue(_principal())
    second_token = service.issue(_principal())

    first_payload = jwt.decode(
        first_token,
        SECRET,
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    second_payload = jwt.decode(
        second_token,
        SECRET,
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )

    assert first_payload["jti"] != second_payload["jti"]


def test_decode_returns_validated_access_token_claims() -> None:
    """Convert a valid JWT into trusted application-level claims."""

    claims = _token_service().decode(_encode(_valid_payload()))

    assert claims.user_id == 17
    assert claims.token_id == "token-id"
    assert claims.token_type == "access"
    assert claims.issued_at.tzinfo is timezone.utc
    assert claims.expires_at > claims.issued_at


def test_decode_rejects_expired_token() -> None:
    """Reject access credentials whose expiration has passed."""

    token = _encode(
        _valid_payload(
            iat=NOW - timedelta(minutes=2),
            nbf=NOW - timedelta(minutes=2),
            exp=NOW - timedelta(minutes=1),
        )
    )

    with pytest.raises(InvalidTokenError):
        _token_service().decode(token)


def test_decode_rejects_modified_signature() -> None:
    """Reject a token whose signed bytes were changed after issuance."""

    token = _encode(_valid_payload())
    header, payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    modified_token = ".".join((header, payload, replacement + signature[1:]))

    with pytest.raises(InvalidTokenError):
        _token_service().decode(modified_token)


def test_decode_rejects_wrong_issuer() -> None:
    """Reject tokens issued by an untrusted authority."""

    token = _encode(_valid_payload(iss="another-issuer"))

    with pytest.raises(InvalidTokenError):
        _token_service().decode(token)


def test_decode_rejects_wrong_audience() -> None:
    """Reject tokens intended for another application audience."""

    token = _encode(_valid_payload(aud="another-api"))

    with pytest.raises(InvalidTokenError):
        _token_service().decode(token)


def test_decode_rejects_wrong_algorithm() -> None:
    """Reject algorithms not selected by trusted server configuration."""

    token = _encode(
        _valid_payload(),
        secret="h" * 48,
        algorithm="HS384",
    )

    with pytest.raises(InvalidTokenError):
        _token_service().decode(token)


def test_decode_rejects_missing_required_claims() -> None:
    """Reject structurally incomplete access tokens."""

    payload = _valid_payload()
    del payload["jti"]

    with pytest.raises(InvalidTokenError):
        _token_service().decode(_encode(payload))


def test_decode_rejects_non_access_token_type() -> None:
    """Prevent refresh or foreign token types from authorizing requests."""

    token = _encode(_valid_payload(type="refresh"))

    with pytest.raises(InvalidTokenError):
        _token_service().decode(token)


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret": "too-short"},
        {"secret": f" {SECRET}"},
        {"issuer": ""},
        {"audience": " api"},
        {"algorithm": "HS384"},
        {"ttl_seconds": 0},
        {"allowed_clock_skew_seconds": -1},
        {"ttl_seconds": 30, "allowed_clock_skew_seconds": 30},
    ],
)
def test_access_token_service_rejects_invalid_configuration(
    overrides: dict[str, object],
) -> None:
    """Fail startup for weak, ambiguous, or unsupported token settings."""

    with pytest.raises(AuthConfigurationError):
        _token_service(**overrides)


def test_refresh_generator_returns_unique_url_safe_tokens() -> None:
    """Generate distinct opaque credentials safe for HTTP transport."""

    generator = RefreshTokenGenerator(token_bytes=32)

    first_token = generator.generate()
    second_token = generator.generate()

    assert first_token != second_token
    assert first_token.isascii()
    assert all(character.isalnum() or character in "-_" for character in first_token)


def test_refresh_digest_is_deterministic() -> None:
    """Produce the same storage digest for the same opaque token."""

    generator = RefreshTokenGenerator(token_bytes=32)
    token = generator.generate()

    assert generator.digest(token) == generator.digest(token)
    assert len(generator.digest(token)) == 64


def test_refresh_digest_changes_for_different_tokens() -> None:
    """Avoid digest collisions for independently generated credentials."""

    generator = RefreshTokenGenerator(token_bytes=32)
    first_token = generator.generate()
    second_token = generator.generate()

    assert generator.digest(first_token) != generator.digest(second_token)


@pytest.mark.parametrize("token_bytes", [0, -1, 1, 31, True])
def test_refresh_generator_rejects_insufficient_entropy(
    token_bytes: object,
) -> None:
    """Require at least 32 bytes of CSPRNG entropy for refresh tokens."""

    with pytest.raises(AuthConfigurationError):
        RefreshTokenGenerator(token_bytes=token_bytes)  # type: ignore[arg-type]


@pytest.mark.parametrize("token", [None, 123, "", " token", "token ", "x" * 1025])
def test_refresh_digest_rejects_invalid_token_input(token: object) -> None:
    """Reject malformed refresh values before computing database digests."""

    with pytest.raises((TypeError, ValueError)):
        RefreshTokenGenerator(token_bytes=32).digest(token)  # type: ignore[arg-type]
