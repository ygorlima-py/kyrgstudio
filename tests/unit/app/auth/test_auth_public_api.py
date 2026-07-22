"""Unit tests for the stable public authentication package API."""

import app.auth as auth
from app.auth.dependencies import get_current_user
from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import PasswordHasher
from app.auth.principal import AuthenticatedPrincipal
from app.auth.service import AuthService
from app.auth.tokens import AccessTokenService


def test_public_api_exports_expected_symbols() -> None:
    """Keep the authentication package root explicit and stable."""

    assert set(auth.__all__) == {
        "AccessTokenService",
        "AuthenticatedPrincipal",
        "AuthService",
        "GoogleTokenVerifier",
        "PasswordHasher",
        "get_current_user",
    }


def test_public_api_does_not_export_internal_stores_or_crypto_helpers() -> None:
    """Keep persistence adapters and concrete crypto helpers module-local."""

    internal_symbols = {
        "Argon2PasswordHasher",
        "AuthStore",
        "RefreshTokenGenerator",
        "SQLAlchemyAuthSessionStore",
        "SQLAlchemyUserStore",
    }

    assert internal_symbols.isdisjoint(auth.__all__)
    assert all(not hasattr(auth, symbol) for symbol in internal_symbols)


def test_public_api_imports_without_circular_dependencies() -> None:
    """Resolve package exports to their concrete definitions during import."""

    assert auth.AccessTokenService is AccessTokenService
    assert auth.AuthenticatedPrincipal is AuthenticatedPrincipal
    assert auth.AuthService is AuthService
    assert auth.GoogleTokenVerifier is GoogleTokenVerifier
    assert auth.PasswordHasher is PasswordHasher
    assert auth.get_current_user is get_current_user
