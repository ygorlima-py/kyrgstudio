"""Stable public API for application authentication.

Concrete persistence adapters, HTTP cookie helpers, and cryptographic
implementation details remain available from their defining modules but are
intentionally excluded from the package root.
"""

from app.auth.dependencies import get_current_user
from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import PasswordHasher
from app.auth.principal import AuthenticatedPrincipal
from app.auth.service import AuthService
from app.auth.tokens import AccessTokenService


__all__ = [
    "AccessTokenService",
    "AuthenticatedPrincipal",
    "AuthService",
    "GoogleTokenVerifier",
    "PasswordHasher",
    "get_current_user",
]
