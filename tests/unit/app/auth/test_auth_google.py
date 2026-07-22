"""Unit tests for verified Google identity token handling."""

from typing import Any, cast

import pytest
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleAuthRequest

from app.auth.google import GoogleTokenVerifier
from app.errors import AuthConfigurationError, InvalidCredentialsError


CLIENT_ID = "web-client.apps.googleusercontent.com"
SECOND_CLIENT_ID = "mobile-client.apps.googleusercontent.com"
ID_TOKEN = "signed-google-id-token"


def _verified_claims(**overrides: object) -> dict[str, object]:
    claims: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "google-subject",
        "email": "User@Example.com",
        "email_verified": True,
        "name": "Ada Lovelace",
        "picture": "https://example.com/avatar.png",
    }
    claims.update(overrides)
    return claims


def _patch_google_verifier(
    monkeypatch: pytest.MonkeyPatch,
    result: dict[str, object] | Exception,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_verify(
        token: str,
        request: GoogleAuthRequest,
        audience: str | list[str] | None = None,
        clock_skew_in_seconds: int = 0,
    ) -> dict[str, object]:
        calls.append(
            {
                "token": token,
                "request": request,
                "audience": audience,
                "clock_skew_in_seconds": clock_skew_in_seconds,
            }
        )
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        "app.auth.google.google_id_token.verify_oauth2_token",
        fake_verify,
    )
    return calls


def test_constructor_accepts_and_deduplicates_valid_client_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve client order while removing duplicate configured audiences."""

    calls = _patch_google_verifier(monkeypatch, _verified_claims())
    verifier = GoogleTokenVerifier(
        client_ids=[CLIENT_ID, SECOND_CLIENT_ID, CLIENT_ID],
    )

    verifier.verify(ID_TOKEN)

    assert calls[0]["audience"] == [CLIENT_ID, SECOND_CLIENT_ID]


@pytest.mark.parametrize(
    "client_ids",
    [[], "client-id", [""], [" client-id"], ["*"], [123]],
)
def test_constructor_rejects_empty_or_invalid_client_ids(
    client_ids: object,
) -> None:
    """Reject missing, ambiguous, or malformed OAuth client configuration."""

    with pytest.raises(AuthConfigurationError):
        GoogleTokenVerifier(client_ids=client_ids)  # type: ignore[arg-type]


def test_verify_uses_google_verifier_with_configured_audience_and_clock_skew(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate cryptographic verification with trusted server settings."""

    calls = _patch_google_verifier(monkeypatch, _verified_claims())
    request = cast(GoogleAuthRequest, object())
    verifier = GoogleTokenVerifier(
        client_ids=[CLIENT_ID],
        allowed_clock_skew_seconds=15,
        request=request,
    )

    verifier.verify(ID_TOKEN)

    assert calls == [
        {
            "token": ID_TOKEN,
            "request": request,
            "audience": CLIENT_ID,
            "clock_skew_in_seconds": 15,
        }
    ]


def test_verify_maps_verified_claims_to_google_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose only normalized identity fields from verified Google claims."""

    _patch_google_verifier(monkeypatch, _verified_claims())

    identity = GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)

    assert identity.subject == "google-subject"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.name == "Ada Lovelace"
    assert identity.avatar_url == "https://example.com/avatar.png"


@pytest.mark.parametrize(
    "issuer",
    ["accounts.google.com", "https://accounts.google.com"],
)
def test_verify_accepts_supported_google_issuers(
    monkeypatch: pytest.MonkeyPatch,
    issuer: str,
) -> None:
    """Accept both issuer forms documented for Google ID tokens."""

    _patch_google_verifier(monkeypatch, _verified_claims(iss=issuer))

    identity = GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)

    assert identity.subject == "google-subject"


def test_verify_rejects_untrusted_issuer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject claims from an issuer outside Google's trusted set."""

    _patch_google_verifier(
        monkeypatch,
        _verified_claims(iss="https://attacker.example.com"),
    )

    with pytest.raises(InvalidCredentialsError):
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)


def test_verify_rejects_unconfigured_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a valid Google identity intended for another OAuth client."""

    _patch_google_verifier(
        monkeypatch,
        _verified_claims(aud=SECOND_CLIENT_ID),
    )

    with pytest.raises(InvalidCredentialsError):
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)


@pytest.mark.parametrize("missing_claim", ["sub", "email", "email_verified"])
def test_verify_rejects_missing_required_claims(
    monkeypatch: pytest.MonkeyPatch,
    missing_claim: str,
) -> None:
    """Reject verified payloads lacking required internal identity claims."""

    claims = _verified_claims()
    del claims[missing_claim]
    _patch_google_verifier(monkeypatch, claims)

    with pytest.raises(InvalidCredentialsError):
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)


@pytest.mark.parametrize("email_verified", [True, False])
def test_verify_preserves_email_verified_claim(
    monkeypatch: pytest.MonkeyPatch,
    email_verified: bool,
) -> None:
    """Preserve Google's verification decision for later service policy."""

    _patch_google_verifier(
        monkeypatch,
        _verified_claims(email_verified=email_verified),
    )

    identity = GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)

    assert identity.email_verified is email_verified


def test_verify_maps_google_auth_failure_to_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate signature and claim failures to the public login error."""

    _patch_google_verifier(monkeypatch, GoogleAuthError("signature failed"))

    with pytest.raises(InvalidCredentialsError):
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)


def test_verify_maps_transport_failure_to_auth_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinguish unavailable Google verification infrastructure."""

    _patch_google_verifier(monkeypatch, TransportError("network unavailable"))

    with pytest.raises(AuthConfigurationError):
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(ID_TOKEN)


@pytest.mark.parametrize(
    "failure",
    [GoogleAuthError("invalid token"), ValueError("invalid claim")],
)
def test_verification_errors_do_not_expose_id_token(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    """Keep submitted Google credentials out of controlled error metadata."""

    sensitive_token = "sensitive-google-token-value"
    _patch_google_verifier(monkeypatch, failure)

    with pytest.raises(InvalidCredentialsError) as captured:
        GoogleTokenVerifier(client_ids=[CLIENT_ID]).verify(sensitive_token)

    error = captured.value
    assert sensitive_token not in str(error)
    assert sensitive_token not in error.technical_message
    assert sensitive_token not in repr(error.details)
