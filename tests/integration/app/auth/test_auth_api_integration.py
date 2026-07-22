"""Integration tests for authentication HTTP routes and browser credentials."""

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.api.exception_handlers import install_exception_handlers
from app.api.routers.auth import router
from app.settings import AppSettings
from app.store.models import AuthSession
from auth_helpers import AuthIntegrationContext, run_async


PASSWORD = "correct-horse-battery-staple"
FRONTEND_ORIGIN = "https://frontend.example.com"
API_BASE_URL = "https://api.example.com"


def _settings() -> AppSettings:
    """Return validated HTTP and auth settings required by the router."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-auth-integration-storage"),
        sqlite_path=Path("/tmp/kyrg-auth-integration.sqlite"),
        database_url="postgresql+asyncpg://integration-placeholder",
        database_echo=False,
        database_pool_size=5,
        database_max_overflow=10,
        database_pool_pre_ping=True,
        openrouter_api_key=None,
        openai_api_key=None,
        gemini_api_key=None,
        default_llm_provider="openrouter",
        default_analysis_model="analysis-model",
        default_adaptation_model="adaptation-model",
        default_transcriber_provider="whisper_local",
        default_transcriber_model="small",
        max_duration_seconds=1800,
        request_timeout_seconds=300,
        celery_broker_url="redis://localhost:6379/0",
        celery_queue_name="kyrg",
        celery_task_soft_time_limit_seconds=300,
        celery_task_time_limit_seconds=360,
        api_cors_origins=(FRONTEND_ORIGIN,),
        auth_refresh_token_ttl_seconds=3600,
        auth_refresh_cookie_name="kyrg_refresh_token",
        auth_refresh_cookie_secure=True,
        auth_refresh_cookie_samesite="lax",
        auth_csrf_cookie_name="kyrg_csrf_token",
    )


def _application(auth_context: AuthIntegrationContext) -> FastAPI:
    """Compose the real auth router with controlled integration resources."""

    application = FastAPI()
    application.state.settings = _settings()
    application.state.auth_service = auth_context.service
    install_exception_handlers(application)
    application.include_router(router)
    return application


def _transport(application: FastAPI) -> httpx.ASGITransport:
    return httpx.ASGITransport(
        app=application,
        raise_app_exceptions=False,
    )


def test_register_sets_protected_refresh_cookie_without_exposing_token(
    auth_context: AuthIntegrationContext,
) -> None:
    """Return access metadata while keeping refresh credentials in cookies."""

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=_transport(_application(auth_context)),
            base_url=API_BASE_URL,
        ) as client:
            response = await client.post(
                "/v1/auth/register",
                json={
                    "email": "user@example.com",
                    "password": PASSWORD,
                    "name": "Ada",
                },
            )

        payload = response.json()
        set_cookie_headers = response.headers.get_list("set-cookie")

        assert response.status_code == 201
        assert payload["token_type"] == "bearer"
        assert payload["access_token"]
        assert "refresh_token" not in payload
        assert response.headers["cache-control"] == "no-store"
        assert any(
            "kyrg_refresh_token=" in header
            and "HttpOnly" in header
            and "Secure" in header
            for header in set_cookie_headers
        )
        assert any(
            "kyrg_csrf_token=" in header and "HttpOnly" not in header
            for header in set_cookie_headers
        )

    run_async(scenario())


def test_me_authenticates_bearer_header_and_ignores_query_token(
    auth_context: AuthIntegrationContext,
) -> None:
    """Authenticate only the Authorization header on the current-user route."""

    async def scenario() -> None:
        application = _application(auth_context)
        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            registration = await client.post(
                "/v1/auth/register",
                json={"email": "user@example.com", "password": PASSWORD},
            )
            access_token = registration.json()["access_token"]
            authenticated = await client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            query_only = await client.get(
                "/v1/auth/me",
                params={"access_token": access_token},
            )

        assert authenticated.status_code == 200
        assert authenticated.json()["email"] == "user@example.com"
        assert "password_hash" not in authenticated.json()
        assert query_only.status_code == 401
        assert query_only.json()["code"] == "authentication_required"
        assert query_only.headers["www-authenticate"] == "Bearer"

    run_async(scenario())


def test_refresh_rotates_cookie_with_valid_csrf_and_origin(
    auth_context: AuthIntegrationContext,
) -> None:
    """Rotate browser credentials only after CSRF and Origin validation."""

    async def scenario() -> None:
        application = _application(auth_context)
        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            registration = await client.post(
                "/v1/auth/register",
                json={"email": "user@example.com", "password": PASSWORD},
            )
            assert registration.status_code == 201
            original_refresh_token = client.cookies.get("kyrg_refresh_token")
            csrf_token = client.cookies.get("kyrg_csrf_token")
            assert original_refresh_token is not None
            assert csrf_token is not None

            refreshed = await client.post(
                "/v1/auth/refresh",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "X-CSRF-Token": csrf_token,
                },
            )
            rotated_refresh_token = client.cookies.get("kyrg_refresh_token")

        async with auth_context.session_factory() as session:
            sessions = list(
                (
                    await session.scalars(
                        select(AuthSession).order_by(AuthSession.id)
                    )
                ).all()
            )

        assert refreshed.status_code == 200
        assert rotated_refresh_token is not None
        assert rotated_refresh_token != original_refresh_token
        assert len(sessions) == 2
        assert sessions[0].revoked_at is not None
        assert sessions[0].replaced_by_session_id == sessions[1].id
        assert sessions[1].revoked_at is None

    run_async(scenario())


def test_refresh_rejects_untrusted_origin_without_rotating_session(
    auth_context: AuthIntegrationContext,
) -> None:
    """Reject cross-site cookie use before the refresh session is modified."""

    async def scenario() -> None:
        application = _application(auth_context)
        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            await client.post(
                "/v1/auth/register",
                json={"email": "user@example.com", "password": PASSWORD},
            )
            csrf_token = client.cookies.get("kyrg_csrf_token")
            assert csrf_token is not None
            response = await client.post(
                "/v1/auth/refresh",
                headers={
                    "Origin": "https://attacker.example.com",
                    "X-CSRF-Token": csrf_token,
                },
            )

        async with auth_context.session_factory() as session:
            sessions = list((await session.scalars(select(AuthSession))).all())

        assert response.status_code == 403
        assert response.json() == {
            "code": "csrf_validation_failed",
            "step": "validating_csrf",
            "details": {},
        }
        assert len(sessions) == 1
        assert sessions[0].revoked_at is None

    run_async(scenario())


def test_logout_revokes_session_and_expires_authentication_cookies(
    auth_context: AuthIntegrationContext,
) -> None:
    """Revoke server-side state and expire both browser credentials."""

    async def scenario() -> None:
        application = _application(auth_context)
        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            await client.post(
                "/v1/auth/register",
                json={"email": "user@example.com", "password": PASSWORD},
            )
            csrf_token = client.cookies.get("kyrg_csrf_token")
            assert csrf_token is not None
            response = await client.post(
                "/v1/auth/logout",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "X-CSRF-Token": csrf_token,
                },
            )

        async with auth_context.session_factory() as session:
            auth_session = (
                await session.execute(select(AuthSession))
            ).scalar_one()

        cookie_headers = response.headers.get_list("set-cookie")
        assert response.status_code == 204
        assert auth_session.revoked_at is not None
        assert sum("Max-Age=0" in header for header in cookie_headers) == 2
        assert response.headers["cache-control"] == "no-store"

    run_async(scenario())


def test_login_hides_account_existence_behind_same_public_error(
    auth_context: AuthIntegrationContext,
) -> None:
    """Return the same HTTP error for an unknown email and a wrong password."""

    async def scenario() -> None:
        application = _application(auth_context)
        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            await client.post(
                "/v1/auth/register",
                json={"email": "user@example.com", "password": PASSWORD},
            )
            unknown = await client.post(
                "/v1/auth/login",
                json={"email": "missing@example.com", "password": "wrong-pass"},
            )
            incorrect = await client.post(
                "/v1/auth/login",
                json={"email": "user@example.com", "password": "wrong-pass"},
            )

        assert unknown.status_code == 401
        assert incorrect.status_code == 401
        assert unknown.json() == incorrect.json()
        assert unknown.json()["code"] == "invalid_credentials"
        assert unknown.headers["www-authenticate"] == "Bearer"
        assert incorrect.headers["www-authenticate"] == "Bearer"

    run_async(scenario())


def test_request_validation_uses_public_error_contract_without_password_leak(
    auth_context: AuthIntegrationContext,
) -> None:
    """Translate malformed HTTP input without reflecting submitted secrets."""

    async def scenario() -> None:
        sensitive_password = "secret-that-must-not-appear"
        async with httpx.AsyncClient(
            transport=_transport(_application(auth_context)),
            base_url=API_BASE_URL,
        ) as client:
            response = await client.post(
                "/v1/auth/register",
                json={
                    "email": "not-an-email",
                    "password": sensitive_password,
                    "unexpected": "field",
                },
            )

        assert response.status_code == 422
        assert response.json()["code"] == "invalid_input"
        assert sensitive_password not in response.text

    run_async(scenario())
