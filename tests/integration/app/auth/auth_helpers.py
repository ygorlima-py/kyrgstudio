"""Shared helpers for authentication integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from app.auth.google import GoogleTokenVerifier
from app.auth.passwords import Argon2PasswordHasher
from app.auth.principal import GoogleIdentity
from app.auth.service import AuthService
from app.auth.tokens import AccessTokenService, RefreshTokenGenerator
from app.auth.transactional_store import AuthStore
from app.store.database import SessionFactory


ResultT = TypeVar("ResultT")
TEST_JWT_SECRET = "integration-test-signing-secret-32-bytes"
TEST_JWT_ISSUER = "kyrg-integration"
TEST_JWT_AUDIENCE = "kyrg-integration-api"


def run_async(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Execute one asynchronous integration scenario from synchronous pytest."""

    return asyncio.run(coroutine)


class StubGoogleTokenVerifier:
    """Return a trusted test identity without contacting Google infrastructure."""

    def __init__(self) -> None:
        self.identity = GoogleIdentity(
            subject="google-integration-subject",
            email="google@example.com",
            email_verified=True,
            name="Google Integration User",
            avatar_url="https://example.com/avatar.png",
        )
        self.received_tokens: list[str] = []

    def verify(self, id_token: str) -> GoogleIdentity:
        self.received_tokens.append(id_token)
        return self.identity


@dataclass(frozen=True, slots=True)
class AuthIntegrationContext:
    """Real authentication components sharing one temporary database."""

    service: AuthService
    store: AuthStore
    session_factory: SessionFactory
    password_hasher: Argon2PasswordHasher
    access_tokens: AccessTokenService
    refresh_tokens: RefreshTokenGenerator
    google_verifier: StubGoogleTokenVerifier


def build_auth_context(
    session_factory: SessionFactory,
) -> AuthIntegrationContext:
    """Compose production auth components with test-safe Argon2 parameters."""

    store = AuthStore(session_factory)
    password_hasher = Argon2PasswordHasher(
        min_password_length=8,
        max_password_length=128,
        time_cost=1,
        memory_cost=8,
        parallelism=1,
        hash_length=16,
        salt_length=8,
    )
    access_tokens = AccessTokenService(
        secret=TEST_JWT_SECRET,
        issuer=TEST_JWT_ISSUER,
        audience=TEST_JWT_AUDIENCE,
        ttl_seconds=900,
        allowed_clock_skew_seconds=0,
    )
    refresh_tokens = RefreshTokenGenerator(token_bytes=32)
    google_verifier = StubGoogleTokenVerifier()
    service = AuthService(
        auth_store=store,
        password_hasher=password_hasher,
        access_token_service=access_tokens,
        refresh_token_generator=refresh_tokens,
        google_token_verifier=cast(
            GoogleTokenVerifier,
            google_verifier,
        ),
        refresh_token_ttl_seconds=3600,
    )
    return AuthIntegrationContext(
        service=service,
        store=store,
        session_factory=session_factory,
        password_hasher=password_hasher,
        access_tokens=access_tokens,
        refresh_tokens=refresh_tokens,
        google_verifier=google_verifier,
    )
