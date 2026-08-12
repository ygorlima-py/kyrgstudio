"""Unit tests for password-recovery authentication routes."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from fastapi import Response
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.api.routers.auth import (
    request_password_reset,
    reset_password,
    router,
)
from app.auth.service import AuthService
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest


ResultT = TypeVar("ResultT")


def run_async(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Run one asynchronous HTTP scenario from a synchronous pytest test."""

    return asyncio.run(coroutine)


class FakeAuthService(AuthService):
    """Record password-recovery calls without touching persistence or email."""

    def __init__(self) -> None:
        self.requested_emails: list[str] = []
        self.reset_requests: list[tuple[str, str]] = []

    async def request_password_reset(self, email: str) -> None:
        """Record the email received from the validated request body."""

        self.requested_emails.append(email)

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> None:
        """Record the token and password passed to the application service."""

        self.reset_requests.append((token, new_password))


def test_forgot_password_accepts_email_and_delegates_to_auth_service() -> None:
    """Normalize the email before delegating the recovery request."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        response = Response()
        result = await request_password_reset(
            ForgotPasswordRequest(email=" USER@Example.COM "),
            response,
            auth_service,
        )

        assert result.accepted is True
        assert auth_service.requested_emails == ["user@example.com"]

    run_async(scenario())


def test_forgot_password_returns_neutral_response_without_sensitive_data() -> None:
    """Avoid revealing whether the submitted email belongs to an account."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        response = Response()
        result = await request_password_reset(
            ForgotPasswordRequest(email="user@example.com"),
            response,
            auth_service,
        )

        assert result.model_dump() == {"accepted": True}
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"

    run_async(scenario())


def test_forgot_password_rejects_invalid_payload_without_calling_service() -> None:
    """Reject malformed email input at the HTTP boundary."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-an-email")

        assert auth_service.requested_emails == []

    run_async(scenario())


def test_forgot_password_rejects_unknown_fields() -> None:
    """Prevent clients from silently sending unsupported recovery data."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(
                email="user@example.com",
                user_id=7,  # type: ignore[call-arg]
            )

        assert auth_service.requested_emails == []

    run_async(scenario())


def test_reset_password_delegates_token_and_new_password() -> None:
    """Pass validated recovery data to AuthService without local business logic."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        response = Response()
        result = await reset_password(
            ResetPasswordRequest(
                token="opaque-reset-token",
                new_password="correct-horse-battery-staple",
            ),
            response,
            auth_service,
        )

        assert result is None
        assert auth_service.reset_requests == [
            (
                "opaque-reset-token",
                "correct-horse-battery-staple",
            )
        ]

    run_async(scenario())


def test_reset_password_does_not_return_token_or_password() -> None:
    """Keep credentials out of the successful HTTP response and cache."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        response = Response()
        await reset_password(
            ResetPasswordRequest(
                token="opaque-reset-token",
                new_password="correct-horse-battery-staple",
            ),
            response,
            auth_service,
        )

        assert response.body == b""
        assert "opaque-reset-token" not in response.body.decode()
        assert "correct-horse-battery-staple" not in response.body.decode()
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"

    run_async(scenario())


def test_reset_password_rejects_invalid_payload_without_calling_service() -> None:
    """Reject short passwords and altered tokens before service delegation."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                token=" altered-token ",
                new_password="short",
            )

        assert auth_service.reset_requests == []

    run_async(scenario())


def test_reset_password_rejects_unknown_fields() -> None:
    """Reject unrelated account data from the password-reset payload."""

    async def scenario() -> None:
        auth_service = FakeAuthService()
        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                token="opaque-reset-token",
                new_password="correct-horse-battery-staple",
                email="user@example.com",  # type: ignore[call-arg]
            )

        assert auth_service.reset_requests == []

    run_async(scenario())


def test_password_recovery_routes_expose_expected_http_contract() -> None:
    """Keep both public routes and their status codes explicitly registered."""

    routes = {
        route.path: route
        for route in router.routes
        if isinstance(route, APIRoute)
    }

    forgot_route = routes["/v1/auth/forgot-password"]
    reset_route = routes["/v1/auth/reset-password"]

    assert forgot_route.methods == {"POST"}
    assert forgot_route.status_code == 202
    assert reset_route.methods == {"POST"}
    assert reset_route.status_code == 204
