"""Unit tests for FastAPI authentication dependencies."""

import asyncio
from collections.abc import Coroutine, Mapping
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

import app.auth.dependencies as auth_dependencies
from app.auth.dependencies import (
    CSRF_HEADER_NAME,
    RefreshCookieCredentials,
    get_auth_service,
    get_current_user,
    get_logout_credentials,
    get_refresh_credentials,
)
from app.auth.principal import AuthenticatedPrincipal
from app.auth.service import AuthService
from app.errors import (
    AuthenticationRequiredError,
    AuthConfigurationError,
    CsrfValidationError,
    RefreshTokenInvalidError,
)
from app.settings import AppSettings


ResultT = TypeVar("ResultT")
FRONTEND_ORIGIN = "https://frontend.example.com"
API_ORIGIN = "https://api.example.com"


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings(
    *,
    cors_origins: tuple[str, ...] = (FRONTEND_ORIGIN,),
) -> AppSettings:
    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-storage"),
        sqlite_path=Path("/tmp/kyrg.sqlite"),
        database_url="sqlite+aiosqlite:///:memory:",
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
        api_cors_origins=cors_origins,
    )


def _request(
    *,
    settings: AppSettings | None = None,
    auth_service: object | None = None,
    headers: Mapping[str, str] | None = None,
    query_string: str = "",
    scheme: str = "https",
    server: tuple[str, int] = ("api.example.com", 443),
) -> Request:
    app = FastAPI()
    if settings is not None:
        app.state.settings = settings
    if auth_service is not None:
        app.state.auth_service = auth_service

    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": scheme,
        "path": "/auth/refresh",
        "raw_path": b"/auth/refresh",
        "query_string": query_string.encode("ascii"),
        "root_path": "",
        "headers": encoded_headers,
        "client": ("127.0.0.1", 50000),
        "server": server,
        "app": app,
    }
    return Request(scope)


def _protected_headers(
    *,
    origin: str = FRONTEND_ORIGIN,
    csrf_cookie: str = "csrf-value",
    csrf_header: str = "csrf-value",
    refresh_token: str = "refresh-token",
) -> dict[str, str]:
    return {
        "Origin": origin,
        CSRF_HEADER_NAME: csrf_header,
        "Cookie": (
            f"kyrg_csrf_token={csrf_cookie}; "
            f"kyrg_refresh_token={refresh_token}"
        ),
    }


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=7,
        email="user@example.com",
        name="Ada",
        auth_provider="password",
        email_verified=True,
    )


class FakeAuthService:
    """Record access-token authentication requested by the dependency."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.principal = _principal()

    async def authenticate_access_token(
        self,
        access_token: str,
    ) -> AuthenticatedPrincipal:
        self.calls.append(access_token)
        return self.principal


def test_get_auth_service_returns_lifespan_service() -> None:
    """Return the exact AuthService instance installed during lifespan."""

    auth_service = object.__new__(AuthService)
    request = _request(auth_service=auth_service)

    assert get_auth_service(request) is auth_service


@pytest.mark.parametrize("configured_service", [None, object()])
def test_get_auth_service_rejects_missing_or_invalid_service(
    configured_service: object | None,
) -> None:
    """Fail safely when API startup did not install a valid AuthService."""

    request = _request(auth_service=configured_service)

    with pytest.raises(AuthConfigurationError):
        get_auth_service(request)


def test_get_current_user_requires_bearer_credentials() -> None:
    """Reject protected requests without an Authorization credential."""

    service = FakeAuthService()

    with pytest.raises(AuthenticationRequiredError):
        _run(
            get_current_user(
                cast(AuthService, service),
                None,
            )
        )

    assert service.calls == []


def test_get_current_user_rejects_wrong_authorization_scheme() -> None:
    """Accept access tokens only through the Bearer authorization scheme."""

    credentials = HTTPAuthorizationCredentials(
        scheme="Basic",
        credentials="access-token",
    )

    with pytest.raises(AuthenticationRequiredError):
        _run(
            get_current_user(
                cast(AuthService, FakeAuthService()),
                credentials,
            )
        )


def test_get_current_user_delegates_access_token_to_auth_service() -> None:
    """Pass the validated header token to the configured authentication service."""

    service = FakeAuthService()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )

    principal = _run(
        get_current_user(
            cast(AuthService, service),
            credentials,
        )
    )

    assert principal is service.principal
    assert service.calls == ["access-token"]


def test_refresh_credentials_require_refresh_cookie() -> None:
    """Reject refresh requests that omit the configured HttpOnly credential."""

    headers = _protected_headers()
    headers["Cookie"] = "kyrg_csrf_token=csrf-value"
    request = _request(settings=_settings(), headers=headers)

    with pytest.raises(RefreshTokenInvalidError):
        _run(get_refresh_credentials(request))


@pytest.mark.parametrize(
    "headers",
    [
        _protected_headers(csrf_cookie="cookie-value", csrf_header="header-value"),
        {
            "Origin": FRONTEND_ORIGIN,
            "Cookie": "kyrg_refresh_token=refresh-token",
        },
        {
            "Origin": FRONTEND_ORIGIN,
            CSRF_HEADER_NAME: "csrf-value",
            "Cookie": "kyrg_refresh_token=refresh-token",
        },
    ],
)
def test_refresh_credentials_require_matching_csrf_cookie_and_header(
    headers: dict[str, str],
) -> None:
    """Require matching double-submit CSRF values for cookie authentication."""

    request = _request(settings=_settings(), headers=headers)

    with pytest.raises(CsrfValidationError):
        _run(get_refresh_credentials(request))


def test_refresh_credentials_compare_csrf_tokens_in_constant_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use a timing-safe comparison for attacker-controlled CSRF values."""

    comparisons: list[tuple[str, str]] = []

    def fake_compare_digest(first: str, second: str) -> bool:
        comparisons.append((first, second))
        return True

    monkeypatch.setattr(
        auth_dependencies.secrets,
        "compare_digest",
        fake_compare_digest,
    )
    request = _request(
        settings=_settings(),
        headers=_protected_headers(),
    )

    credentials = _run(get_refresh_credentials(request))

    assert credentials.refresh_token == "refresh-token"
    assert comparisons == [("csrf-value", "csrf-value")]


@pytest.mark.parametrize(
    "headers",
    [
        {
            CSRF_HEADER_NAME: "csrf-value",
            "Cookie": (
                "kyrg_csrf_token=csrf-value; "
                "kyrg_refresh_token=refresh-token"
            ),
        },
        _protected_headers(origin="https://attacker.example.com"),
        {
            **_protected_headers(),
            "Origin": "null",
        },
    ],
)
def test_refresh_credentials_require_trusted_origin_or_referer(
    headers: dict[str, str],
) -> None:
    """Reject cookie mutations without a trusted browser origin."""

    request = _request(settings=_settings(), headers=headers)

    with pytest.raises(CsrfValidationError):
        _run(get_refresh_credentials(request))


def test_refresh_credentials_accept_configured_cors_origin() -> None:
    """Accept a protected refresh request from an explicit frontend origin."""

    request = _request(
        settings=_settings(),
        headers=_protected_headers(origin=FRONTEND_ORIGIN),
    )

    credentials = _run(get_refresh_credentials(request))

    assert credentials == RefreshCookieCredentials(
        refresh_token="refresh-token"
    )


def test_refresh_credentials_accept_same_origin_request() -> None:
    """Trust the API's own normalized origin in addition to configured CORS."""

    request = _request(
        settings=_settings(cors_origins=()),
        headers=_protected_headers(origin=API_ORIGIN),
    )

    credentials = _run(get_refresh_credentials(request))

    assert credentials.refresh_token == "refresh-token"


def test_logout_credentials_apply_same_cookie_csrf_and_origin_rules() -> None:
    """Protect logout with exactly the same cookie mutation checks as refresh."""

    valid_request = _request(
        settings=_settings(),
        headers=_protected_headers(),
    )
    invalid_request = _request(
        settings=_settings(),
        headers=_protected_headers(csrf_header="different"),
    )

    assert _run(get_logout_credentials(valid_request)).refresh_token == (
        "refresh-token"
    )
    with pytest.raises(CsrfValidationError):
        _run(get_logout_credentials(invalid_request))


@pytest.mark.parametrize(
    ("configured_origin", "request_origin"),
    [
        ("https://frontend.example.com", "HTTPS://FRONTEND.EXAMPLE.COM:443"),
        ("http://frontend.example.com", "HTTP://FRONTEND.EXAMPLE.COM:80"),
    ],
)
def test_origin_normalization_handles_default_ports_and_case(
    configured_origin: str,
    request_origin: str,
) -> None:
    """Normalize scheme, host case, and default ports before comparison."""

    request = _request(
        settings=_settings(cors_origins=(configured_origin,)),
        headers=_protected_headers(origin=request_origin),
    )

    assert _run(get_refresh_credentials(request)).refresh_token == (
        "refresh-token"
    )


def test_credentials_never_accept_tokens_from_query_parameters() -> None:
    """Ignore access and refresh credentials supplied in the request URL."""

    service = FakeAuthService()
    request = _request(
        settings=_settings(),
        headers={
            "Origin": FRONTEND_ORIGIN,
            CSRF_HEADER_NAME: "csrf-value",
            "Cookie": "kyrg_csrf_token=csrf-value",
        },
        query_string=(
            "access_token=query-access&refresh_token=query-refresh"
        ),
    )

    with pytest.raises(AuthenticationRequiredError):
        _run(get_current_user(cast(AuthService, service), None))
    with pytest.raises(RefreshTokenInvalidError):
        _run(get_refresh_credentials(request))

    assert service.calls == []
