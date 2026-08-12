"""Integration tests for the password-recovery HTTP flow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.api.exception_handlers import install_exception_handlers
from app.api.routers.auth import router
from app.store.models import AuthSession, PasswordResetToken, User
from auth_helpers import (
    AuthIntegrationContext,
    CapturedEmail,
    run_async,
)


OLD_PASSWORD = "old-correct-horse"
NEW_PASSWORD = "new-correct-horse"
API_BASE_URL = "https://api.example.com"


def _application(context: AuthIntegrationContext) -> FastAPI:
    """Compose the real auth router with the shared integration service."""

    application = FastAPI()
    application.state.auth_service = context.service
    install_exception_handlers(application)
    application.include_router(router)
    return application


def _transport(application: FastAPI) -> httpx.ASGITransport:
    """Create an in-process ASGI transport for integration requests."""

    return httpx.ASGITransport(
        app=application,
        raise_app_exceptions=False,
    )


def _extract_reset_token(email: CapturedEmail) -> str:
    """Extract the browser-fragment token from a captured reset link."""

    reset_url = email.template_values["reset_url"]
    token_values = parse_qs(urlsplit(reset_url).fragment).get("token", [])

    if len(token_values) != 1:
        raise AssertionError("Captured reset email does not contain one token")

    return token_values[0]


async def _create_password_user(
    context: AuthIntegrationContext,
) -> User:
    """Create one verified local user for a recovery scenario."""

    user_record = await context.store.create_password_user(
        email="user@example.com",
        password_hash=context.password_hasher.hash(OLD_PASSWORD),
        name="Ada Lovelace",
    )
    await context.store.mark_user_email_verified(user_record.user_id)

    async with context.session_factory() as session:
        return (
            await session.execute(
                select(User).where(User.id == user_record.user_id)
            )
        ).scalar_one()


def test_forgot_password_sends_hashed_token_and_neutral_response(
    auth_context: AuthIntegrationContext,
) -> None:
    """Issue a reset email while persisting only the token digest."""

    async def scenario() -> None:
        user = await _create_password_user(auth_context)

        async with httpx.AsyncClient(
            transport=_transport(_application(auth_context)),
            base_url=API_BASE_URL,
        ) as client:
            response = await client.post(
                "/v1/auth/forgot-password",
                json={"email": "USER@example.com"},
            )

        assert response.status_code == 202
        assert response.json() == {"accepted": True}
        assert response.headers["cache-control"] == "no-store"
        assert len(auth_context.email_sender.messages) == 1
        captured_email = auth_context.email_sender.messages[0]
        assert captured_email.recipient == user.email

        raw_token = _extract_reset_token(captured_email)
        assert raw_token in captured_email.template_values["reset_url"]

        async with auth_context.session_factory() as session:
            reset_token = (
                await session.execute(
                    select(PasswordResetToken).where(
                        PasswordResetToken.user_id == user.id
                    )
                )
            ).scalar_one()

        assert reset_token.token_hash != raw_token
        assert len(reset_token.token_hash) == 64
        assert raw_token not in reset_token.token_hash

    run_async(scenario())


def test_reset_password_updates_hash_revokes_sessions_and_is_single_use(
    auth_context: AuthIntegrationContext,
) -> None:
    """Replace the password atomically and reject reuse of the same token."""

    async def scenario() -> None:
        user = await _create_password_user(auth_context)
        await auth_context.store.create_session(
            user_id=user.id,
            token_hash="active-refresh-token-hash",
            family_id="password-reset-test-family",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        async with httpx.AsyncClient(
            transport=_transport(_application(auth_context)),
            base_url=API_BASE_URL,
        ) as client:
            await client.post(
                "/v1/auth/forgot-password",
                json={"email": user.email},
            )
            raw_token = _extract_reset_token(
                auth_context.email_sender.messages[0]
            )
            reset_response = await client.post(
                "/v1/auth/reset-password",
                json={
                    "token": raw_token,
                    "new_password": NEW_PASSWORD,
                },
            )
            reuse_response = await client.post(
                "/v1/auth/reset-password",
                json={
                    "token": raw_token,
                    "new_password": "another-password",
                },
            )

        assert reset_response.status_code == 204
        assert reset_response.content == b""
        assert reset_response.headers["cache-control"] == "no-store"
        assert reuse_response.status_code == 422
        assert reuse_response.json() == {
            "code": "invalid_input",
            "step": "validating_input",
            "details": {"field": "token"},
        }

        async with auth_context.session_factory() as session:
            stored_user = (
                await session.execute(
                    select(User).where(User.id == user.id)
                )
            ).scalar_one()
            stored_session = (
                await session.execute(
                    select(AuthSession).where(AuthSession.user_id == user.id)
                )
            ).scalar_one()
            stored_token = (
                await session.execute(select(PasswordResetToken))
            ).scalar_one()

        assert auth_context.password_hasher.verify(
            NEW_PASSWORD,
            stored_user.password_hash,
        )
        assert not auth_context.password_hasher.verify(
            OLD_PASSWORD,
            stored_user.password_hash,
        )
        assert stored_session.revoked_at is not None
        assert stored_token.used_at is not None

    run_async(scenario())


def test_forgot_password_keeps_unknown_email_response_neutral(
    auth_context: AuthIntegrationContext,
) -> None:
    """Avoid account enumeration when the requested email does not exist."""

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=_transport(_application(auth_context)),
            base_url=API_BASE_URL,
        ) as client:
            response = await client.post(
                "/v1/auth/forgot-password",
                json={"email": "missing@example.com"},
            )

        assert response.status_code == 202
        assert response.json() == {"accepted": True}
        assert auth_context.email_sender.messages == []

    run_async(scenario())
