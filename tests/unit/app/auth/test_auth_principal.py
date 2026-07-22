"""Unit tests for immutable authentication data contracts."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.principal import (
    AccessTokenClaims,
    AuthenticatedPrincipal,
    GoogleIdentity,
    IssuedAuthTokens,
)


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def _access_token_claims(**overrides: object) -> AccessTokenClaims:
    values = {
        "user_id": 7,
        "token_id": "token-id",
        "issued_at": NOW,
        "not_before": NOW,
        "expires_at": NOW + timedelta(minutes=15),
    }
    values.update(overrides)
    return AccessTokenClaims(**values)  # type: ignore[arg-type]


def _issued_tokens(**overrides: object) -> IssuedAuthTokens:
    values = {
        "access_token": "access-secret",
        "refresh_token": "refresh-secret",
        "access_token_expires_at": NOW + timedelta(minutes=15),
        "refresh_token_expires_at": NOW + timedelta(days=30),
    }
    values.update(overrides)
    return IssuedAuthTokens(**values)  # type: ignore[arg-type]


def test_authenticated_principal_normalizes_verified_identity() -> None:
    """Normalize verified identity fields before exposing them to the app."""

    principal = AuthenticatedPrincipal(
        user_id=7,
        email="  USER@Example.COM ",
        name="  Ada Lovelace  ",
        auth_provider="  GOOGLE ",
        email_verified=True,
    )

    assert principal.user_id == 7
    assert principal.email == "user@example.com"
    assert principal.name == "Ada Lovelace"
    assert principal.auth_provider == "google"
    assert principal.email_verified is True


def test_authenticated_principal_is_immutable() -> None:
    """Prevent request identity from changing after authentication."""

    principal = AuthenticatedPrincipal(
        user_id=7,
        email="user@example.com",
        name=None,
        auth_provider="password",
        email_verified=True,
    )

    with pytest.raises(FrozenInstanceError):
        principal.email = "other@example.com"  # type: ignore[misc]


@pytest.mark.parametrize("user_id", [0, -1, True, 1.5, "7"])
def test_authenticated_principal_rejects_invalid_user_id(
    user_id: object,
) -> None:
    """Require a positive integer user identifier."""

    with pytest.raises((TypeError, ValueError)):
        AuthenticatedPrincipal(
            user_id=user_id,  # type: ignore[arg-type]
            email="user@example.com",
            name=None,
            auth_provider="password",
            email_verified=True,
        )


@pytest.mark.parametrize(
    "email",
    ["", "missing-at.example.com", "@example.com", "user@", "a@b@c.com"],
)
def test_authenticated_principal_rejects_invalid_email(email: str) -> None:
    """Reject malformed addresses before constructing a principal."""

    with pytest.raises(ValueError):
        AuthenticatedPrincipal(
            user_id=7,
            email=email,
            name=None,
            auth_provider="password",
            email_verified=True,
        )


def test_google_identity_normalizes_verified_claims() -> None:
    """Normalize trusted claims received from the Google verifier."""

    identity = GoogleIdentity(
        subject="  google-subject  ",
        email="  USER@Example.COM ",
        email_verified=True,
        name="  Ada  ",
        avatar_url="  https://example.com/avatar.png  ",
    )

    assert identity.subject == "google-subject"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.name == "Ada"
    assert identity.avatar_url == "https://example.com/avatar.png"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("subject", " "),
        ("email", "invalid-email"),
        ("email_verified", "true"),
        ("name", 123),
        ("avatar_url", 123),
    ],
)
def test_google_identity_rejects_invalid_claims(
    field_name: str,
    invalid_value: object,
) -> None:
    """Reject claims that do not satisfy the internal identity contract."""

    values: dict[str, object] = {
        "subject": "google-subject",
        "email": "user@example.com",
        "email_verified": True,
        "name": None,
        "avatar_url": None,
    }
    values[field_name] = invalid_value

    with pytest.raises((TypeError, ValueError)):
        GoogleIdentity(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["issued_at", "not_before", "expires_at"])
def test_access_token_claims_require_timezone_aware_dates(
    field_name: str,
) -> None:
    """Reject ambiguous token timestamps without timezone information."""

    with pytest.raises(ValueError, match="timezone"):
        _access_token_claims(**{field_name: datetime(2026, 7, 22, 12, 0)})


@pytest.mark.parametrize(
    "overrides",
    [
        {"expires_at": NOW},
        {"expires_at": NOW - timedelta(seconds=1)},
        {
            "not_before": NOW + timedelta(minutes=16),
            "expires_at": NOW + timedelta(minutes=15),
        },
    ],
)
def test_access_token_claims_reject_invalid_date_order(
    overrides: dict[str, datetime],
) -> None:
    """Require a coherent validity window for access-token claims."""

    with pytest.raises(ValueError):
        _access_token_claims(**overrides)


def test_access_token_claims_require_access_token_type() -> None:
    """Keep refresh or foreign token types out of access-token claims."""

    with pytest.raises(ValueError, match="token_type"):
        _access_token_claims(token_type="refresh")


def test_issued_auth_tokens_require_bearer_token_type() -> None:
    """Expose only the supported bearer authentication scheme."""

    with pytest.raises(ValueError, match="token_type"):
        _issued_tokens(token_type="basic")


def test_issued_auth_tokens_require_refresh_expiry_after_access_expiry() -> None:
    """Require refresh credentials to outlive their paired access token."""

    with pytest.raises(ValueError, match="refresh_token_expires_at"):
        _issued_tokens(
            refresh_token_expires_at=NOW + timedelta(minutes=15),
        )


def test_token_contract_repr_hides_token_values() -> None:
    """Prevent token secrets from leaking through logs and debugging output."""

    tokens = _issued_tokens()

    rendered = repr(tokens)

    assert "access-secret" not in rendered
    assert "refresh-secret" not in rendered
    assert "access_token='" not in rendered
    assert "refresh_token='" not in rendered
